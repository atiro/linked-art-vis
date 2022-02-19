import csv
import json
from collections import OrderedDict, Counter

# Read in various CSV, output provencance data in JSON format

artworks = OrderedDict()
artists = []
owners = OrderedDict()
provenance = OrderedDict()
art_prov = []

with open('artworks.csv') as csvfile:
    artwork_reader = csv.DictReader(csvfile)
    for row in artwork_reader:
        if row['copy'] != 1:
          print("%s - %s" % (row['id'], row['title']))
          artworks[row['id']] = [row['title'], row['artist'], row['date']]

#print(json.dumps(artworks))

with open('artists.csv') as csvfile:
    artists_reader = csv.DictReader(csvfile)
    for row in artists_reader:
      artists.append([row['artist']])

with open('owners.csv') as csvfile:
    owners_reader = csv.DictReader(csvfile)
    for row in owners_reader:
      owners[row['id']] = row['owner']

with open('provenance.csv') as csvfile:
    provenance_reader = csv.DictReader(csvfile)
    for row in provenance_reader:
      if row['artwork'] not in provenance:
        provenance[row['artwork']] = [ [row['owner'], row['date'] ] ]
      else:
        provenance[row['artwork']].append([row['owner'], row['date']])

# First we go 

top_node_id = 1


## Version 2 - Sunburst showing ownership (todo configure generations, eg. every 50 years ?) 
# Assumption ownership is unknown unless later ownership states relationship (bought from)

prov_ownership = []

prov_ownership.append( { 'id': top_node_id, "name": "Art Treasures - Modern Artworks" } )

year_segment_node_id = 2

prov_ownership.append( { 'id': year_segment_node_id , 'name': "1857" , 'size': 4, 
            'year': 1857, 'parent': top_node_id} )

# Need to calculate totals per circle for sizing. For first generation go through all with parent 1

# Then go through provenance, we need to remove from the list once we have dealt with it so we now when
# there are no more provenance moves to track

node_id = 3

collection_sizes = {}
collection_nodes = {}

origin_year = 1857
start_year = 1900
end_year = 2021
ring_year  = 1900

for work_prov in provenance:
 prov_statement = provenance[work_prov]
 if int(prov_statement[0][1]) == origin_year:
   if owners[prov_statement[0][0]] in collection_sizes:
     collection_sizes[owners[prov_statement[0][0]]][owners[prov_statement[0][0]]] += 1
   else:
     collection_sizes[owners[prov_statement[0][0]]] = Counter()
     collection_sizes[owners[prov_statement[0][0]]][owners[prov_statement[0][0]]] += 1

for coll_owner in collection_sizes:
#    print("Artwork Node: %d Artwork: %s" % (node_id, artworks[artwork][0]))
#    prov_ownership.append( { 'id': node_id, 'name': coll_owner,  collection_sizes[coll_owner], 'parent': top_node_id } )

    prov_ownership.append( { 'id': node_id, 'name': coll_owner,  'parent': top_node_id, 'origin_size': collection_sizes[coll_owner][coll_owner]  } )

    # Save for the first owner, then subsequence owner mapping from owner to node
    # Subsequent ownership mapping updated with each ring

    collection_nodes[coll_owner] = {}
    collection_nodes[coll_owner][coll_owner] = node_id

    print("Collection %s Node: %s" % (coll_owner, node_id))
    node_id += 1

# Then per X years, go through each owner, checking what prov information we have. If none


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

      if owners[seg_owner] not in segments_prov:
        print("Resetting segement %s" % seg_owner)
        segments_prov[owners[seg_owner]] = {}

    print("Prov moves for artwork %s" % artworks[work_prov][0])

    # For each artwork, go through the provenance events to look for anything
    # relevant for this ring
    # Skip first prov as we've already handled the first owner (for start date)

    # We need to save this in case there is more than one prov move within the period, we only want to track the move from first
    # to last owner within the period

    orig_owner = provenance[work_prov][0][0]

    ring_moves = 0

#    print(provenance[work_prov][1:])

    for index, prov_statement in enumerate(provenance[work_prov][1:], start=1):

      print(prov_statement)

      # What do we need to handle

      # Find the last provenance move that applies to this ring. That could either be the last one before the ring
      # year, or if there is one after it we take that as applying for all rings in-between (if no other prov statements)


      # Does the prov move fall within the period for this ring
      if int(prov_statement[1]) > (ring_year - 50) and int(prov_statement[1]) <= ring_year:
        new_owner = prov_statement[0]
        print("(Ring: %d) Prov move in last 50 years for %s from %s to %s in %d" % (ring_year, work_prov, owners[prev_owner],
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
#            print("Last known owner will be reset to original owner for this ring %s" % cur_ring_owners[work_prov])
        else:
          print("Not setting last known owner for %s" % artworks[work_prov][0])
        break
      elif int(prov_statement[1]) > ring_year:
          # We've gone past the current year so stop looking now (no, this will stop us looking for last known holder)
        print("Gone past ring year with prov statements")
        break
      else:
        # Must be a move before current ring, we just need to update prev owner
        print("Updating prev owner to %s as this prov move was in %d" % (owners[prov_statement[0]], int(prov_statement[1])))
        prev_owner = prov_statement[0]
#        print("Not relevant prov statement for artwork '%s' for year %s (prov year %d)" % (artworks[work_prov][0], ring_year,
#            int(prov_statement[1])))
#        print("Index %d Num Prov %d" % (index+1, len(provenance[work_prov])))

      if ring_moves > 0:
            # We've already moved once for this ring, so keep the prev_owner
        print("We have had at least one ring move already")
        prev_owner = prov_statement[0]
#      else:
#        print("Keeping original owner as prev_owner")
#        prev_owner = orig_owner
 
    # We only care about who it went from before the current ring, not intermittent owners within the period
    print("Resetting ring prev owner to %s" % owners[prev_owner])
    prev_owner = cur_ring_owners[work_prov]

    # Now update for next ring

    if new_owner > 0:
      print("Setting new ring owner to %s" % owners[new_owner])
      cur_ring_owners[work_prov] = new_owner

      # Handle unknown ownership, e.g. from 1879 to 2021
#      else:
#        print("Default to current owner")
#        new_owner = prev_owner

      # If we don't have a previos owner (because it started less than X years before 2nd ring, we just take
      # the first one

    # Update counts for owners for this segment in the ring

    if new_owner > 0:
        prov_moves += 1
        if owners[prev_owner] in segments_prov[owners[seg_owner]]:
          print("(new with prev) Prov move at year %d from %s to %s for seg %s" % (ring_year, owners[prev_owner], owners[new_owner],
              owners[seg_owner]))
          segments_prov[owners[seg_owner]][owners[prev_owner]][owners[new_owner]] += 1
        else:
          print("(new no prev) Prov move at year %d from %s to %s for seg %s" % (ring_year, owners[prev_owner], owners[new_owner],
              owners[seg_owner]))
          print("Creating new owner segment in current ring")
          segments_prov[owners[seg_owner]][owners[prev_owner]] = Counter()
          segments_prov[owners[seg_owner]][owners[prev_owner]][owners[new_owner]] += 1
#      else:
#        # We don't have any more provenane, record as unknown
#        if prev_owner in ring_provs:
#          print("(no new, prev owner) Prov move for %s at year %d from %s to Unknown" % (work_prov, ring_year, prev_owner))
#          ring_provs[prev_owner]['Unknown'] += 1
#        else:
#          print("(no new, no prev) Prov move for %s at year %d from %s to Unknown" % (work_prov, ring_year, prev_owner))
#          ring_provs[prev_owner] = Counter()
#          ring_provs[prev_owner]['Unknown'] += 1


      # Update prev owner if we are still looking for a new statement relevant to the ring

#    if new_owner > 0:
#      print("Updating prev owner for next loop")
#      prev_owner = new_owner
#    else:
#      prev_owner = cur_owner

#    else:
#        print("NO new owner")

  # Now we have at year X,for each previous owner, a count of artworks now owner by new owners
  # (or the same owner, or Unknown)
  # We need to create new nodes for each new owner (including the same owner) with parent point to the
  # prev one
  # Write out node and size


  print("Finished scanning provenance moves\n\n")

  seen_collections = []

  print("Found %d provenance events for this ring" % prov_moves)

  owner_nodes = {}

  # STEP 2 - Now we write the nodes out for this ring

  # For each origin owner
  for seg_owner in segments_prov:
    print("Handling prov moves for segment %s in year %d" % (seg_owner, ring_year))
    print(segments_prov[seg_owner])

    owner_nodes[seg_owner] = {}

    # For all the owners from the previous ring segment
    for prev_owner in segments_prov[seg_owner]:
      print("Seg owner: %s Prev owner: %s" % (seg_owner, prev_owner))
      initial_coll_size = collection_sizes[seg_owner][prev_owner]
      print("Current owner collection size %s" % (initial_coll_size) )

      known_prov_count = 0
      print("Ring prov move from current owner %s (for segment %s)" % (prev_owner, seg_owner))

      seen_collections.append(prev_owner)

      # For all the new owners from previous ring segment owners
      for new_owner in segments_prov[seg_owner][prev_owner]:
        print("Current Owner: %s New Owner: %s" % (prev_owner, new_owner))

        # If it's just continuation of ownership we skip this and handle it in the general sweep below
        if seg_owner == new_owner and prev_owner == new_owner:
            print("Origin ownership retained, skipping adding a move")
            continue
#        elif prev_owner == new_owner:
#            print("Current ownership retained, skipping adding a move")
#            continue

#       if new_owner not in collection_nodes:
#           prov_ownership.append( { 'id': node_id, 'name': new_owner, 'size': 1, 'parent': collection_nodes[collection] } )
#           node_id += 1

       # Add segment in this ring linked to the prev owner in the previous ring (parent)

        print("Linking new owner %s to current owner %s with new node id %d and current owner node id %s" % 
                (new_owner, prev_owner, node_id, collection_nodes[seg_owner][prev_owner]))

        # We don't both writing the text out for every ring if it's the same owner as before, except for first and last
        if (prev_owner == new_owner) and ((ring_year == start_year) or (ring_year == end_year)):
          prov_ownership.append( { 'id': node_id, 'name': new_owner, 'size': 1, 'year': ring_year,
            'parent': collection_nodes[seg_owner][prev_owner] } )
        else:
          prov_ownership.append( { 'id': node_id, 'name': new_owner, 'size': 1, 'year': ring_year,
              'seen': 1, 'parent': collection_nodes[seg_owner][prev_owner] } )

       # Update this owner new node in the ring. What to do if it's the same owner ?
        #collection_nodes[seg_owner][new_owner] = node_id
        owner_nodes[seg_owner][new_owner] = node_id

        collection_sizes[seg_owner][new_owner] += 1

       # We don't need to handle this one for this ring (TODO same problem if artwork moves between two current 
       # owners)
        seen_collections.append(new_owner)

        # PROBLEM (see below) - if this is just proof remained in same collection we end up incrementing and decreamting
        # the same number so no change 
        collection_sizes[seg_owner][prev_owner] -= 1

        print("Reducing current owner %s collection size to %d" % (prev_owner, collection_sizes[seg_owner][prev_owner]))

        node_id += 1

        known_prov_count += 1

    # STEP 2A

    # All the remaining for that prev_owner are assumed to be in existing ownership (or should this be unknown ?)

    # PROBLEM - When we know a subset of moves for the owner e.g. Royal Academy has 12 paintsing in 1950, we know one
    # exists in their collection still in 2021, we end up creating two rings here, the first above with 1, then because
    # we update the node_id there, the remaining ones below 


    if (collection_sizes[seg_owner][prev_owner] > 0) and (known_prov_count < initial_coll_size):
      print("Now filling in gaps for current owner %s (known prov moves %d, remaining collection size %s)" % (prev_owner,
        known_prov_count, collection_sizes[seg_owner][prev_owner]))

      # We don't both writing the text out for every ring if it's the same owner as before, except for first and last
      if (ring_year == start_year) or (ring_year == end_year):

         print("Showing text as first/last ring")
         prov_ownership.append( { 'id': node_id, 'name': prev_owner, 'size': collection_sizes[seg_owner][prev_owner],
            'year': ring_year, 'parent': collection_nodes[seg_owner][prev_owner] } )
      else:
         print("Not showing text as not first/last ring")
         prov_ownership.append( { 'id': node_id, 'name': prev_owner, 'size': collection_sizes[seg_owner][prev_owner],
            'year': ring_year, 'same': 1, 'parent': collection_nodes[seg_owner][prev_owner] } )

      print("Linking remaining collection for existing owner %s from new node id %d to node id %d" % 
              (prev_owner, node_id, collection_nodes[seg_owner][prev_owner]))

      collection_nodes[seg_owner][prev_owner] = node_id

      # Hmm, if an owner acquires an artwork from one of the other owners, the collection size changes, so we need to
      # track if per segment each time (not some new id for segments)

      node_id += 1

    # Now we can update all the ownership links as we have nothing else to add in this ring

    for seg_owner in owner_nodes:
      for new_owner in owner_nodes[seg_owner]:
        collection_nodes[seg_owner][new_owner] = owner_nodes[seg_owner][new_owner]

    # Update collection node_id for next ring (this need to be per segement)

    #collection_nodes[prev_owner] = node_id

  # STEP 3 - We now need to handle all those with no prov information for this ring. Mark as Unknown (if the owners remained the
  # same, would already be handled (e.g. if observed to remain in same collection in 2021

  # PROB - How to add same flag (as if no prov info for this ring for artwork,. same ownership is not handled as above, so will
  # be added here.

  for seg_owner in collection_nodes:
    for new_owner in collection_nodes[seg_owner]:
      if new_owner not in seen_collections and (collection_sizes[seg_owner][new_owner] > 0):
        print("Filling in segment %s for owner %s for year %d with size %d (node %d, parent %d)" % (seg_owner, 
            new_owner, ring_year, 
            collection_sizes[seg_owner][new_owner], node_id,
            collection_nodes[seg_owner][new_owner]))
        prov_ownership.append( { 'id': node_id, 'name': new_owner, 'size': collection_sizes[seg_owner][new_owner], 'hide': 1,
            'year': ring_year, 'parent': collection_nodes[seg_owner][new_owner]} )
        collection_nodes[seg_owner][new_owner] = node_id
        node_id += 1
        # Once it goes unknown, we need to remove it from the original collection
      else:
        print("Seen provenance for %s so not filling in segment" % seg_owner)

  first = False

  # STEP 4 - Finally Add the year as a segment (only way at the moment I can see to show this)

  prov_ownership.append( { 'id': node_id, 'name': "%s" % ring_year, 'size': 20, 'ring': 1, 
            'year': ring_year, 'parent': year_segment_node_id} )

  year_segment_node_id = node_id
  node_id += 1

  ring_year += 50

  if ring_year > 2021:
      ring_year = 2021


#node_id = 10000

#for prov in provenance:
#  prev_owner_node = int(prov) + 2
#  for artwork_prov in provenance[prov]:
#    print("Artwork %s - Node: %d Owner: %s Name: %s Parent: %s" % (prov, node_id, artwork_prov[0], owners[artwork_prov[0]], prev_owner_node))
#    art_prov.append( { 'id': node_id, 'name': owners[artwork_prov[0]], 'parent': prev_owner_node } )
#    prev_owner_node = node_id
#    node_id += 1

with open("art-his-prov.json", "w") as art_fp:
  json.dump(prov_ownership, art_fp)

# To write out the main issue is ID assignment
# Artworks run from 1 to 1,000,000
# Provanance moves run from 1,000,000

