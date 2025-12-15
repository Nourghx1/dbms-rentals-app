# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Apartments(models.Model):
    aid = models.IntegerField(db_column='aID', primary_key=True)  # Field name made lowercase.
    city = models.CharField(max_length=50, blank=True, null=True)
    roomsnum = models.IntegerField(db_column='roomsNum', blank=True, null=True)  # Field name made lowercase.
    ownerid = models.ForeignKey('Owners', models.DO_NOTHING, db_column='ownerID')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Apartments'


class Owners(models.Model):
    ownerid = models.IntegerField(db_column='ownerID', primary_key=True)  # Field name made lowercase.
    oname = models.CharField(db_column='oName', max_length=50, blank=True, null=True)  # Field name made lowercase.
    residencecity = models.CharField(db_column='residenceCity', max_length=50, blank=True, null=True)  # Field name made lowercase.
    bdate = models.DateField(db_column='bDate', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Owners'


class Rentals(models.Model):
    renterid = models.IntegerField(db_column='renterID')  # Field name made lowercase. The composite primary key (renterID, rYear) found, that is not supported. The first column is selected.
    ryear = models.IntegerField(db_column='rYear')  # Field name made lowercase.
    aid = models.ForeignKey(Apartments, models.DO_NOTHING, db_column='aID')  # Field name made lowercase.
    cost = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Rentals'
        unique_together = (('renterid', 'ryear'),)
