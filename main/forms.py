from django import forms
class ChampionBusquedaForm(forms.Form):
    champion_name = forms.CharField(label="Nombre de Campeon", widget=forms.TextInput, required=True)

class PlayerBusquedaForm(forms.Form):
    player_name = forms.CharField(label="Nombre de Jugador", widget=forms.TextInput, required=True)
        