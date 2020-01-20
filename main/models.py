from django.db import models
from django.core.validators import MinValueValidator,MaxValueValidator,URLValidator

class Champion(models.Model):
    idChampion = models.AutoField(primary_key = True)
    name = models.CharField(verbose_name='Name', max_length=30)
    image = models.URLField(max_length=200)
    tiers = models.ManyToManyField('Tier', through='Tier')

    def __str__(self):
        return self.name + ' ' + self.image

    class Meta:
        ordering = ('name',)

class Skill(models.Model):
    idSkill = models.AutoField(primary_key = True)
    name = models.CharField(verbose_name='Name', max_length=30)
    description = models.CharField(verbose_name='Description')
    video = models.URLField(max_length=200)
    champion = models.ForeignKey('Champion', verbose_name='Champion', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name + ' ' + self.description + ' ' + self.video

    class Meta:
        ordering = ('name', 'description')

class Position(models.Model):
    idPosition = models.AutoField(primary_key = True)
    name = models.CharField(verbose_name='Position', max_length=30)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)

class Tier(models.Model):
    idChampion = models.ForeignKey(Champion,on_delete=models.CASCADE)
    idPosition = models.ForeignKey(Position,on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

    def __str__(self):
        return self.rating

    class Meta:
        ordering = ('rating',)