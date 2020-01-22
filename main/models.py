from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, URLValidator


class Champion(models.Model):
    idChampion = models.AutoField(primary_key=True)
    name = models.CharField(verbose_name='Name', max_length=30)
    image = models.URLField(max_length=200)
    releaseDate = models.DateField(verbose_name='Release date')

    def __str__(self):
        return self.name + ' ' + self.image

    class Meta:
        ordering = ('name',)


class Skill(models.Model):
    idSkill = models.AutoField(primary_key=True)
    name = models.CharField(verbose_name='Name', max_length=30)
    description = models.CharField(verbose_name='Description', max_length=3000)
    video = models.URLField(max_length=200)
    champion = models.ForeignKey('Champion', verbose_name='Champion', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name + ' ' + self.description + ' ' + self.video

    class Meta:
        ordering = ('name', 'description')


class Position(models.Model):
    idPosition = models.AutoField(primary_key=True)
    name = models.CharField(verbose_name='Position', max_length=30)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class Tier(models.Model):
    idTier = models.AutoField(primary_key=True)
    level = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)])
    idChampion = models.ForeignKey(Champion, on_delete=models.CASCADE, related_name='idChampionTier')
    idPosition = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='idPositionTier')
    idsChampionCounter = models.ManyToManyField('Champion', related_name='ChampionCounter')
    idsChampionStronger = models.ManyToManyField('Champion', related_name='ChampionStronger')
    winrate = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return self.level

    class Meta:
        ordering = ('level',)


class Player(models.Model):
    idPlayer = models.AutoField(primary_key=True)
    name = models.CharField(verbose_name='Name', max_length=40)
    urlPerfil = models.URLField(max_length=200)
    ranking = models.CharField(verbose_name='ranking', max_length=30)
    winrate = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    idsChampion = models.ManyToManyField('Champion')

    def __str__(self):
        return self.name + ' ' + self.ranking + ' ' + self.winrate

    class Meta:
        ordering = ('name', 'ranking', 'winrate')
