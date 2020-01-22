from django import forms

POSITION = [
    ('Bot','Bot'),
    ('Top','Top'),
    ('Mid','Mid'),
    ('Jungle','Jungle'),
    ('Support','Support')]

LEVEL = [
    (1,1),
    (2,2),
    (3,3),
    (4,4),
    (5,5)]

class ChampionBusquedaForm(forms.Form):
    champion_name = forms.CharField(label="Nombre de Campeon", widget=forms.TextInput, required=True)

class PlayerBusquedaForm(forms.Form):
    player_name = forms.CharField(label="Nombre de Jugador", widget=forms.TextInput, required=True)

class TierBusquedaForm(forms.Form):
    tier_level = forms.CharField(label="Nivel de los campeones", widget=forms.TextInput, required=True)

class PositionBusquedaForm(forms.Form):
    positionName = forms.CharField(label="Posición de los campeones", widget=forms.RadioSelect(choices=POSITION), required=True)

class PositionTierBusquedaForm(forms.Form):
    level = forms.CharField(label="Nivel de los campeones", widget=forms.RadioSelect(choices=LEVEL), required=True)
    positionName = forms.CharField(label="Posición de los campeones", widget=forms.RadioSelect(choices=POSITION), required=True)

class ChampionDatesBusquedaForm(forms.Form):
    startDate = forms.DateField(label="Fecha de inicio", widget=forms.TextInput, required=True)
    endDate = forms.DateField(label="Fecha de fin", widget=forms.TextInput, required=True)