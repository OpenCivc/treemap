# psql otm; update treemap_user set is_superuser='t' where username='pmeserve';
import json
from django.contrib.gis.geos import Point, Polygon
from treemap.models import Instance
from treemap.models import Plot
from treemap.models import Species
from treemap.models import Tree
from treemap.models import User
from treemap.ecobenefits import TreeBenefitsCalculator
from django.db import connection
from django.db.models import Max

import treemap.species

cursor = connection.cursor()

# Tree.objects.count()
# Plot.objects.count()
# # 106 = max built-in specie ID
# Tree.objects.all().delete()
# Plot.objects.all().delete()
# cursor.execute("DELETE FROM treemap_species WHERE id > 106")

# ruby:
# t = trees['features'].detect{ |t| t['properties']['objectid'] == 15933}

# (-9201414.22227, 4238028.93819) 1465 Sand Hill Rd>

# /usr/local/otm/app/opentreemap/ows.json
# user = User.objects.all()[0]
user = User.objects.get(username = 'pmeserve')
city = Instance.objects.all()[0]
f = open('ows.json', 'r')
trees = json.load(f)

# Species(instance=city).user_can_create(user)

# for s in treemap.species.SPECIES:
#   if Species.objects.filter(otm_code=s['otm_code']).exists():
#     print "Species %s already exists, skipping" % s['otm_code']
#     continue
#   print "creating species %s" % s['otm_code']
#   cursor.execute("INSERT INTO treemap_species (instance_id, max_diameter, max_height, udfs, flowering_period, fruit_or_nut_period, fact_sheet_url, plant_guide_url, genus, species, cultivar, common_name, otm_code, other_part_of_name) VALUES (%s, 200, 800, '', '', '', '', '', %s, %s, %s, %s, %s, %s)", [city.id, s['genus'], s['species'], s['cultivar'], s['common_name'], s['otm_code'], s['other_part_of_name']])

#tree = trees['features'][0]
# execfile('import.py')

for tree in trees['features']:
  tp = tree['properties']
  # broken
  if tp['id'] in [12265, 12266, 14157]: # "bad" trees w/ weird unicode/characters that won't import
    continue
  if Tree.objects.filter(id=tp['id']).exists():
    print "Tree %s already exists, skipping" % tp['id']
    continue
  print "creating tree: %s : %s" % (tp['id'], tree['geometry']['coordinates'])
  geom = Point(tree['geometry']['coordinates'], srid=4326)
  geom.transform(3857)
  plot = Plot(id=tp['id'], geom=geom, instance=city, address_street=tp['geocoded_address'])
  plot.save_with_user(user)
  species = None
  date_planted = None
  date_removed = None
  canopy_height = 0.1
  diameter = 0.1
  if tp['species_id'] is not None:
    print "species: %s, %s, %s" % (tp['scientific_name'], tp['common_name'], tp['species_id'])
    try:
      species = Species.objects.get(common_name = tp['common_name'])
    except:
      print "couldn't find species"
      try:
        cursor.execute("INSERT INTO treemap_species (instance_id, max_diameter, max_height, udfs, flowering_period, fruit_or_nut_period, fact_sheet_url, plant_guide_url, genus, species, cultivar, common_name, otm_code, other_part_of_name) VALUES (%s, 200, 800, '', '', '', '', '', %s, %s, %s, %s, %s, %s)", [city.id, tp['scientific_name'], '', '', tp['common_name'], tp['species_id'], ''])
        species = Species.objects.get(otm_code = tp['species_id'])
      except:
        print "exception"
  if tp['date_planted'] is not None:
    date_planted = tp['date_planted'].split()[0]
  if tp['date_removed'] is not None:
    date_removed = tp['date_removed'].split()[0]
  if tp['canopy_height'] > 0:
    canopy_height = tp['canopy_height']
  if tp['dbh'] > 0:
    diameter = tp['dbh']
  if tp['height'] > 0:
    height = tp['height']
  t = Tree(id=tp['id'], diameter=diameter, height=height, canopy_height=canopy_height, date_planted=date_planted, date_removed=date_removed, plot=plot, instance=city, species=species)
  t.save_with_user(user)

max_plot_id = Plot.objects.all().aggregate(Max('id'))['id__max']
max_tree_id = Tree.objects.all().aggregate(Max('id'))['id__max']

cursor.execute("ALTER SEQUENCE treemap_mapfeature_id_seq RESTART WITH %s" % (max_plot_id + 1))
cursor.execute("ALTER SEQUENCE treemap_tree_id_seq RESTART WITH %s" % (max_tree_id + 1))
