from django import forms

class ChampionBusquedaForm(forms.Form):
    champion_name = forms.CharField(label="Nombre de Campeon", widget=forms.TextInput, required=True)

class PlayerBusquedaForm(forms.Form):
    player_name = forms.CharField(label="Nombre de Jugador", widget=forms.TextInput, required=True)

class TierBusquedaForm(forms.Form):
    tier_level = forms.CharField(label="Nivel de los campeones", widget=forms.TextInput, required=True)

class PositionBusquedaForm(forms.Form):
    position_name = forms.CharField(label="Posición de los campeones", widget=forms.TextInput, required=True)

class PositionTierBusquedaForm(forms.Form):
    level = forms.CharField(label="Nivel de los campeones", widget=forms.TextInput, required=True)
    positionName = forms.CharField(label="Posición de los campeones", widget=forms.TextInput, required=True)