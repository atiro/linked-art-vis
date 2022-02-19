# Generate data structure for Vega visualisation to show provenance relationships for a set of
# artworks from some initial point in time (exhibition, sale, listing, etc)
# Visualisation quality varies with the data but roughly works for around 100 artworks. 
# Moves are binned per period of time chosen (decade, quarter century, etc, whatever suits) but
# this does mean multiple ownership changes within that time are not visible, only the last owner
# is shown

# This is slightly hardcoded for the two initial datasets it was used with
#
#   - Manchester Art Treasures (Modern Artworks Gallery)
#   - Sonderbund 1912 Exhibition (with thanks to Open Art Data)

import csv
import json
import textwrap
from collections import OrderedDict, Counter

# Hand entered CSV is used as a starting point to store the data needed, but ultimately this
# should be generated from the Linked Art common data model to allow multiple sources of data
# (a platform for this is needed, and to allow people to select the authority they want for
# provenance history)

# Read in various CSV (artworks, artists, owners, provenance history) - output the provenance data structure
# for Vega to read.

artworks = OrderedDict()
artists = {}
owners = OrderedDict()
provenance = OrderedDict()
art_prov = []
last_owner_node = {}
prov_ownership = []

collection_sizes = {} # Keep track of the current number of artworks for every owner, so we can tell if any changed ownership
collection_nodes = {} # Keep track of the mapping between an owner and their current node_id in the visualisation

visualisation_title = "Artworks of 1912"

origin_year = 1912
start_year = 1920
end_year = 2021
ring_year  = 1920

with open('artworks.csv') as csvfile:
    artwork_reader = csv.DictReader(csvfile)
    for row in artwork_reader:
        # Ignore a copy of an artwork
        if row['copy'] != 1:
#          print("%s - %s" % (row['id'], row['title']))
          artworks[row['id']] = [row['title'], row['artist'], row['date']]


with open('artists.csv') as csvfile:
    artists_reader = csv.DictReader(csvfile)
    for row in artists_reader:
      artists[row['id']] = row['artist']

with open('owners.csv') as csvfile:
    owners_reader = csv.DictReader(csvfile)
    for row in owners_reader:
      owners[row['id']] = row['owner']
      # Initialise a "last owner" dict with all the initial owners, so we can retrieve the right one at the end
      # (otherwise if we just go on the last owner, we can't tell (if they appear more than once) which artwork they ended up
      # owning started where)
      last_owner_node[row['id']] = {}

with open('provenance.csv') as csvfile:
    provenance_reader = csv.DictReader(csvfile)
    for row in provenance_reader:
      if row['artwork'] not in provenance:
        provenance[row['artwork']] = [ [row['owner'], row['date'] ] ]
      else:
        provenance[row['artwork']].append([row['owner'], row['date']])

# Node id is used in the visualisation data to link between elements. We need a top node for the starting point

top_node_id = 1

prov_ownership.append( { 'id': top_node_id, "name": visualisation_title } )

year_segment_node_id = 2

# This is a hack to be able to show the year of each ring in the visualisation, by faking an ownership segment

prov_ownership.append( { 'id': year_segment_node_id , 'name': str(origin_year) , 'size': 20, 
            'year': origin_year, 'parent': top_node_id} )




# From this point node_id is incremented when we have a provenance move, so we can link the prev/cur owners

node_id = 3


# First we need to calculate the initial collection sizes per owner 

for work_prov in provenance:
 prov_statement = provenance[work_prov]
 if int(prov_statement[0][1]) == origin_year:
   if prov_statement[0][0] in collection_sizes:
     collection_sizes[prov_statement[0][0]][prov_statement[0][0]] += 1
   else:
     collection_sizes[prov_statement[0][0]] = Counter()
     collection_sizes[prov_statement[0][0]][prov_statement[0][0]] = 1

# For the first circle add all them all with a parent node_id of 1 (the starting point)

for coll_owner in collection_sizes:
    prov_ownership.append( { 'id': node_id, 'name': textwrap.wrap(owners[coll_owner], width=12),  'parent': top_node_id, 'origin_size': collection_sizes[coll_owner][coll_owner]  } )

    # Start saving the owner to node_id mappings

    collection_nodes[coll_owner] = {}
    collection_nodes[coll_owner][coll_owner] = node_id

#    print("Collection %s Node: %s" % (coll_owner, node_id))

    node_id += 1

# Now we start creating the data for each ring. Per X years, go through each owner, checking what prov information we have.

first = True
last_ring = False

segments_prov = {}
orig_ring_owners = {}
cur_ring_owners = {}

while (ring_year <= end_year) and not last_ring:

  print("\n\nPROV FOR YEAR %d\n\n" % ring_year)

  if ring_year == end_year:
      last_ring = True

  ring_provs = {}

  # Clear the previous ring counts

  for seg in segments_prov:
      segments_prov[seg] = {}

    # STEP 1 - For each artwork, go through all the prov statements, checking if we know where it it at
    # this point in time (or, if we know it has not/will not change ownership)

  prov_moves = 0

  for work_prov in provenance:
    prev_owner = provenance[work_prov][0][0]
    new_owner = -1
    seg_owner = -1

    print("Dealing with provenance for %s" % (artworks[work_prov][0]))

    # First time through we save the owner so we can use for the orig owner segment tracking
    if work_prov not in orig_ring_owners:
        orig_ring_owners[work_prov] = prev_owner

    # Keep track of who owns the work at the start of the ring
    if work_prov not in cur_ring_owners:
        cur_ring_owners[work_prov] = prev_owner

    # We need this ensure we get the right collection node, need to work through the rings from this
    # starting segment to the (prev) owner the next owner gets the artwork from, to avoid clash when
    # the same owner appears twice in the ring (e.g. Tate)
    if seg_owner < 0:
      # Set the root of the tree from which all move for this artworks are traced (the owner at start
      # point)
      seg_owner = orig_ring_owners[work_prov]

      if seg_owner not in segments_prov:
        print("Resetting segement %s" % seg_owner)
        segments_prov[seg_owner] = {}

    print("Prov moves for artwork %s" % artworks[work_prov][0])

    # For each artwork, go through the provenance events to look for anything
    # relevant for this ring
    # Skip first prov as we've already handled the first owner (for start date)

    # We need to save this in case there is more than one prov move within the period, we only want to track the move from first
    # to last owner within the period

    orig_owner = provenance[work_prov][0][0]

    ring_moves = 0

    for index, prov_statement in enumerate(provenance[work_prov][1:], start=1):

      # Find the last provenance move that applies to this ring. That could either be the last one before the ring
      # year, or if there is one after it we take that as applying for all rings in-between (if no other prov statements)

      # Does the prov move fall within the period for this ring
      if int(prov_statement[1]) > (ring_year - 10) and int(prov_statement[1]) <= ring_year:
        new_owner = prov_statement[0]
        print("(Ring: %d) Prov move in last 10 years for %s from %s to %s in %d" % (ring_year, artworks[work_prov], owners[prev_owner],
            owners[new_owner], int(prov_statement[1])))
        # There could be a second move that supercedes this one so we don't stop looking
        # break
        ring_moves += 1
      elif index == len(provenance[work_prov]) - 1: 
        # If the previous prov statement isn't still to be processed, then this is the last statement
        # so we stick with that owner from now on
        print("Checking if prev statement year %s is less than ring year %s" % (provenance[work_prov][index-1][1], ring_year))
        print("Checking if statement year %s is more than ring year %s" % (prov_statement[1], ring_year))
        if(int(provenance[work_prov][index-1][1]) < ring_year) and (int(prov_statement[1]) > ring_year):
            if(prov_statement[0] == provenance[work_prov][index-1][0]): 
              new_owner = prev_owner
              print("Last known owner %s sames as prev owner %s (could be same owner to present day" % 
                      (owners[prov_statement[0]], owners[provenance[work_prov][index-1][0]]))
            else:
              print("Last known owner %s different to prev owner %s, no update" % (provenance[work_prov][index-1][0],
                  prov_statement[0]))
        else:
          print("Not setting last known owner for %s" % artworks[work_prov][0])
        break
      elif int(prov_statement[1]) > ring_year:
          # We've gone past the current year so stop looking now 
        print("Gone past ring year with prov statements")
        break
      else:
        # Must be a move before current ring, we just need to update prev owner
        print("Updating prev owner to %s as this prov move was in %d" % (owners[prov_statement[0]], int(prov_statement[1])))
        prev_owner = prov_statement[0]

      if ring_moves > 0:
        # We've already moved once for this ring, so keep the prev_owner
        print("We have had at least one ring move already")
        prev_owner = prov_statement[0]
 
    # We only care about who it went from before the current ring, not intermittent owners within the period
    print("Resetting ring prev owner from %s... " % owners[prev_owner])
    prev_owner = cur_ring_owners[work_prov]
    print("...to %s for tracking further moves within this ring" % owners[prev_owner])

    # Now update for next ring

    if new_owner > 0:
      print("Setting new ring owner to %s" % owners[new_owner])
      cur_ring_owners[work_prov] = new_owner

    # If we don't have a previous owner (because it started less than X years before 2nd ring, we just take
    # the first one

    # Now update counts for owners for this segment in the ring

    if new_owner > 0:
        prov_moves += 1
        if prev_owner in segments_prov[seg_owner]:
          print("(new with prev) Prov move at year %d from %s to %s for seg %s" % (ring_year, owners[prev_owner], owners[new_owner],
              owners[seg_owner]))
          segments_prov[seg_owner][prev_owner][new_owner] += 1
        else:
          print("(new no prev) Prov move at year %d from %s to %s for seg %s" % (ring_year, owners[prev_owner], owners[new_owner],
              owners[seg_owner]))
          print("Creating new owner segment in current ring")
          segments_prov[seg_owner][prev_owner] = Counter()
          segments_prov[seg_owner][prev_owner][new_owner] += 1

  # Now we have at year X, for each previous owner, a count of artworks now
  # owned by the new owners (or the same owner, or Unknown)
  # We need to create new nodes for each new owner (including the same owner)
  # with parent point to the # prev one
  # Write out node and size

  print("Finished scanning provenance moves\n\n")


  print("Found %d provenance events for this ring" % prov_moves)


  # STEP 2 - Now we write the nodes out for this ring
  # We go through all the known moves, then we fill out the rest on the assumption they stay with the last known owner (is this true?)

  # Record those owners we have already seen  (need to do per segment in case two different moves for same owner in same ring)

  seen_collections = {}
  owner_nodes = {}

  # For each origin owner
  for seg_owner in segments_prov:
    print("Handling prov moves for segment %s in year %d" % (owners[seg_owner], ring_year))
    print(segments_prov[seg_owner])

    owner_nodes[seg_owner] = {}
    seen_collections[seg_owner] = {}

    # For all the owners from the previous ring segment
    for prev_owner in segments_prov[seg_owner]:
      print("Seg owner: %s Prev owner: %s" % (owners[seg_owner], owners[prev_owner]))
      initial_coll_size = collection_sizes[seg_owner][prev_owner]
      print("Current owner collection size %s" % (initial_coll_size) )

      known_prov_count = 0
      print("Ring prov move from current owner %s (for segment %s)" % (owners[prev_owner], owners[seg_owner]))

      seen_collections[seg_owner][prev_owner] = 1

      # For all the new owners from previous ring segment owners
      for new_owner in segments_prov[seg_owner][prev_owner]:
        print("Current Owner: %s New Owner: %s" % (owners[prev_owner], owners[new_owner]))

        # If it's just continuation of ownership we skip this and handle it in the general sweep below
        if seg_owner == new_owner and prev_owner == new_owner:
            print("Origin ownership retained, skipping adding a move")
            continue
        elif prev_owner == new_owner:
            print("Current ownership retained, skipping adding a move")
            continue

       # Add segment in this ring linked to the prev owner in the previous ring (parent)

        print("Linking new owner %s to current owner %s with new node id %d and current owner node id %s" % 
                (owners[new_owner], owners[prev_owner], node_id, collection_nodes[seg_owner][prev_owner]))

        # We don't both showing the name for every ring if it's the same owner as before, except for first and last
        if (prev_owner == new_owner) and ((ring_year == start_year) or (ring_year == end_year)):
          prov_ownership.append( { 'id': node_id, 'name': textwrap.wrap(owners[new_owner], width=12), 'size': segments_prov[seg_owner][prev_owner][new_owner], 'year': ring_year, 'parent': collection_nodes[seg_owner][prev_owner] } )
          print("Setting last owner for '%s' to node id %d" % (work_prov, node_id))
          last_owner_node[seg_owner][new_owner] = node_id
        else:
          prov_ownership.append( { 'id': node_id, 'name': textwrap.wrap(owners[new_owner], width=12), 'size': segments_prov[seg_owner][prev_owner][new_owner], 'year': ring_year, 'seen': 1, 'parent': collection_nodes[seg_owner][prev_owner] } )
          print("Setting last owner for '%s' to node id %d" % (work_prov, node_id))
          last_owner_node[seg_owner][new_owner] = node_id

       # Update this owner new node in the ring. What to do if it's the same owner ?
        #collection_nodes[seg_owner][new_owner] = node_id
        owner_nodes[seg_owner][new_owner] = node_id

        collection_sizes[seg_owner][new_owner] += segments_prov[seg_owner][prev_owner][new_owner]

       # We don't need to handle this one for this ring (TODO same problem if artwork moves between two current 
       # owners)
        seen_collections[seg_owner][new_owner] = 1

        # PROBLEM (see below) - if this is just proof remained in same collection we end up incrementing and decreamting
        # the same number so no change 
        collection_sizes[seg_owner][prev_owner] -= segments_prov[seg_owner][prev_owner][new_owner]

        print("Reducing current owner %s collection size to %d" % (prev_owner, collection_sizes[seg_owner][prev_owner]))

        node_id += 1

        known_prov_count += 1

    # STEP 2A

    # All the remaining for that prev_owner are assumed to be in existing ownership (or should this be unknown ?)

      print("Prev owner %s coll size: %s" % (owners[prev_owner], collection_sizes[seg_owner][prev_owner]))

      if (collection_sizes[seg_owner][prev_owner] > 0) and (known_prov_count < initial_coll_size):
        print("Now filling in gaps for current owner %s (known prov moves %d, remaining collection size %s)" % (owners[prev_owner],
        known_prov_count, collection_sizes[seg_owner][prev_owner]))

      # We don't both writing the text out for every ring if it's the same owner as before, except for first and last
        if (ring_year == start_year) or (ring_year == end_year):

          print("Showing text as first/last ring")
          prov_ownership.append( { 'id': node_id, 'name': textwrap.wrap(owners[prev_owner], width=12), 'size': collection_sizes[seg_owner][prev_owner], 'year': ring_year, 'parent': collection_nodes[seg_owner][prev_owner] } )
          last_owner_node[seg_owner][new_owner] = node_id
          print("Setting last owner for '%s' to node id %d" % (work_prov, node_id))
        else:
          print("Not showing text as not first/last ring")
          prov_ownership.append( { 'id': node_id, 'name': textwrap.wrap(owners[prev_owner], width=12), 'size': collection_sizes[seg_owner][prev_owner], 'year': ring_year, 'same': 1, 'parent': collection_nodes[seg_owner][prev_owner] } )
          print("Linking remaining collection for existing owner %s from new node id %d to node id %d" % 
              (prev_owner, node_id, collection_nodes[seg_owner][prev_owner]))
          last_owner_node[seg_owner][new_owner] = node_id
          print("Setting last owner for '%s' to node id %d" % (work_prov, node_id))

        collection_nodes[seg_owner][prev_owner] = node_id

      # Hmm, if an owner acquires an artwork from one of the other owners, the collection size changes, so we need to
      # track if per segment each time (not some new id for segments)

        node_id += 1

    # Now we can update all the ownership links as we have nothing else to add in this ring

    for seg_owner in owner_nodes:
      for new_owner in owner_nodes[seg_owner]:
        collection_nodes[seg_owner][new_owner] = owner_nodes[seg_owner][new_owner]

    # Update collection node_id for next ring (this need to be per segement)

  # STEP 3 - We now need to handle all those with no prov information for this ring. Mark as Unknown (if the owners remained the
  # same, would already be handled (e.g. if observed to remain in same collection in 2021

  print("\nNO PROV MOVES - %d\n\n" % ring_year)

  for seg_owner in collection_nodes: # For owner in 1912
    for new_owner in collection_nodes[seg_owner]: # For new owners for this year
      if new_owner not in seen_collections[seg_owner] and (collection_sizes[seg_owner][new_owner] > 0):
        print("Filling in segment %s for owner %s for year %d with size %d (node %d, parent %d)" % (owners[seg_owner], 
            owners[new_owner], ring_year, 
            collection_sizes[seg_owner][new_owner], node_id,
            collection_nodes[seg_owner][new_owner]))
        prov_ownership.append( { 'id': node_id, 'name': textwrap.wrap(owners[new_owner], width=12), 'size': collection_sizes[seg_owner][new_owner],
            'same': 1, 'year': ring_year, 'parent': collection_nodes[seg_owner][new_owner]} )
        last_owner_node[seg_owner][new_owner] = node_id
        print("Setting last owner for '%s' to node id %d" % (work_prov, node_id))
        collection_nodes[seg_owner][new_owner] = node_id
        node_id += 1
        # Once it goes unknown, we need to remove it from the original collection
      else:
        print("Seen provenance for seg owner %s and new owner %s (coll size %d) so not filling in segment" % (owners[seg_owner], 
            owners[new_owner], collection_sizes[seg_owner][new_owner]))

  first = False

  # STEP 4 - Finally add the year as a segment so it can be shown on the visualisation

  prov_ownership.append( { 'id': node_id, 'name': "%s" % ring_year, 'size': 5, 'ring': 1, 
            'year': ring_year, 'parent': year_segment_node_id} )

  year_segment_node_id = node_id
  node_id += 1

  ring_year += 10

  if ring_year > 2021:
      ring_year = 2021



# STEP 5 - Write out names/artists of artworks to show as outer text ring around it all 

# Two problems. Some last owners appear more than once, we need to make sure we attached the right artwork to the right occurrence
# Second, some segments end with more than one artwork with the same last owner, we need to position the names otherwise they
# are written on top of each other

# Track how many works the last owner has 
last_owner_count = {}
seen_last_owner = {}

print("\nAdding artworks names to current owner\n\n")

for artwork in provenance:
  # Get last owner
  orig_owner = provenance[artwork][0][0]
  last_owner = provenance[artwork][-1][0]

# Problem - if same first/last owner for more than one artwork, how to handle. we could say "and X more" but we don't know X until
# we have already added them already. Otherwise we could add a count to each and in the visualisation use that to shift them by X
# but again we don't know how many to fit in until we get to the end of them (e.g. should it be thirds, half, quarter, etc)

# Only occurs for one case in 1912 dataset, Kode Bergen

#  if orig_owner in seen_last_owner:
#      if last_owner in seen_last_owner[orig_owner]:
#          seen_last_owner[orig_owner][last_owner] += 1

#  print("Artwork %s" % artwork)
#  print("Artwork artist %s" % artworks[artwork])

  maker_text = textwrap.wrap(artworks[artwork][0], width=12)
  maker_text += ["by"]
  maker_text += textwrap.wrap(artists[artworks[artwork][1]], width=12)

  prov_ownership.append( { 'id': node_id, 'name': maker_text,
      'size': 1, 'artwork' : 1, 'year': 2021, 'parent': last_owner_node[orig_owner][last_owner] })

  node_id += 1

# STEP 6 - Write out totals per owners in 2021 for a ring around the it all
# TDOo (not sure if this will make sense, as will be next to unrelated segments in last ring)


# STEP 7 - Write it all out!

with open("art-his-prov.json", "w") as art_fp:
  json.dump(prov_ownership, art_fp)

