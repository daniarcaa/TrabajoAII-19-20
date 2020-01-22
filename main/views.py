import re

import urllib.request
import os
from bs4 import BeautifulSoup
from django.shortcuts import render
from collections import Counter
from whoosh import qparser
from whoosh.fields import DATETIME, TEXT, ID, NUMERIC, Schema
from whoosh.index import create_in, open_dir
from whoosh.qparser import MultifieldParser, QueryParser
from django.conf import settings

from datetime import datetime
from main.forms import ChampionBusquedaForm, PlayerBusquedaForm, TierBusquedaForm, PositionBusquedaForm, PositionTierBusquedaForm, ChampionDatesBusquedaForm
from django.db.models import Avg, Count
from main.models import Champion, Skill, Position, Tier, Player

import pandas as pd
from astropy.table import QTable, Table, Column
from astropy import units as u
import numpy as np

from sklearn.metrics.pairwise import cosine_similarity

from sklearn.feature_extraction.text import CountVectorizer

from rake_nltk import Rake


def index(request):
    return render(request, 'index.html', {'STATIC_URL': settings.STATIC_URL})


def getChampsInfo():
    main_directory = 'info_champ'
    champions_directory = main_directory + '/' + 'champions'
    skills_directory = main_directory + '/' + 'skills'
    positions_directory = main_directory + '/' + 'positions'
    tiers_directory = main_directory + '/' + 'tiers'
    if not os.path.exists(main_directory):
        os.mkdir(main_directory)
    if not os.path.exists(champions_directory):
        os.mkdir(champions_directory)
    if not os.path.exists(skills_directory):
        os.mkdir(skills_directory)
    if not os.path.exists(positions_directory):
        os.mkdir(positions_directory)
    if not os.path.exists(tiers_directory):
        os.mkdir(tiers_directory)

    ix1 = create_in(champions_directory, schema=schemaChampions())
    ix2 = create_in(skills_directory, schema=schemaSkill())
    ix3 = create_in(positions_directory, schema=schemaPosition())
    ix4 = create_in(tiers_directory, schema=schemaTier())
    writer1 = ix1.writer()
    writer2 = ix2.writer()
    writer3 = ix3.writer()
    writer4 = ix4.writer()

    # Añadimos las posiciones al esquema de posiciones
    writer3.add_document(idPosition=1, name='Bot')
    writer3.add_document(idPosition=2, name='Mid')
    writer3.add_document(idPosition=3, name='Jungle')
    writer3.add_document(idPosition=4, name='Top')
    writer3.add_document(idPosition=5, name='Support')
    writer3.commit()
    print('Se han indexado ' + str(5) + ' posiciones')

    # Empezamos el scraping de los campeones y su información
    count_champion = 1
    count_skill = 1
    url_statistics = 'https://euw.op.gg/champion/statistics'
    url_releases = 'https://lol.gamepedia.com/Portal:Champions/List'
    file_statistics = urllib.request.urlopen(url_statistics)
    file_release = urllib.request.urlopen(url_releases)
    parser_statistics = BeautifulSoup(file_statistics, 'html.parser')
    parser_release = BeautifulSoup(file_release, 'html.parser')
    champions_statistics = parser_statistics.find_all(
        lambda tag: tag.name == 'div' and 'champion-index__champion-item' in tag.get('class') and 'tip' not in tag.get('class'))
    champions_release = parser_release.find('table', class_=[
                                            'sortable', 'wikitable', 'smwtable', 'jquery-tablesorter']).find_all('tr')[1:]

    # Diccionarios para almacenar datos temporalmente
    name_id_champ = {}
    name_positions_champ = {}
    name_position_tier = {}
    name_position_counters_champs = {}
    name_position_strong_against_champs = {}
    name_position_winrate = {}
    name_release_date = {}

    # Fechas de salidas de los campeones
    for c in champions_release:
        champ_name = c.find_all('td')[0].find('a')['title']
        if champ_name == 'Nunu':
            champ_name = 'Nunu & Willump'
        release_date = c.find_all('td')[-2].string.strip()
        release_date = datetime.strptime(release_date, '%Y-%m-%d')
        name_release_date[champ_name] = release_date

    for c in champions_statistics:
        champ_stadics = c.find('a')['href']
        champ_stadics = 'https://euw.op.gg/' + champ_stadics
        file2 = urllib.request.urlopen(champ_stadics)
        parser2 = BeautifulSoup(file2, 'html.parser')
        champ_info = parser2.find('div', class_='l-champion-statistics-header')
        # Nombre e imagen del campeón
        champ_name = champ_info.find(
            'h1', class_='champion-stats-header-info__name').string
        champ_image = champ_info.find(
            'div', class_='champion-stats-header-info__image').find('img')['src']
        name_id_champ[champ_name] = count_champion

        # Habilidades del campeón
        skills = champ_info.find_all('div', class_='champion-stat__skill')
        for s in skills:
            html_skill = s['title']
            html_skill = html_skill.replace('<br>', '\n').replace(
                '<br/>', '\n').replace('<br />', '\n')
            parser_skill = BeautifulSoup(html_skill, 'html.parser')
            skill_name = parser_skill.find('b').string
            if skill_name is None:
                skill_name = ''
            skill_description = parser_skill.find(
                lambda tag: tag.name == 'span' and not tag.attrs)
            if skill_description is None:
                skill_description = ''
            else:
                skill_description = skill_description.text
            skill_video = s.find('a')['href']

            # Añadimos las hablidades al esquema de habilidades
            writer2.add_document(idSkill=count_skill, name=skill_name,
                                 description=skill_description, video=skill_video, idChampion=count_champion)
            count_skill = count_skill + 1

        # Posiciones del campeón
        positions = champ_info.find_all(
            'li', class_='champion-stats-header__position')
        position_list = []
        for p in positions:
            position_list.append(
                p.find('span', class_='champion-stats-header__position__role').string)
        name_positions_champ[champ_name] = position_list
        position_tier = {}
        position_counters_champs = {}
        position_strong_against_champs = {}
        position_winrate = {}
        for p in position_list:
            if p == 'Middle':
                p = 'Mid'
            if p == 'Bottom':
                p = 'Bot'
            champ_position_url = champ_stadics + '/' + p
            file3 = urllib.request.urlopen(champ_position_url)
            parser3 = BeautifulSoup(file3, 'html.parser')
            champ_info = parser3.find(
                'div', class_='l-champion-statistics-header')

            # Nivel del campeón según la posición
            tier = champ_info.find(
                'div', class_='champion-stats-header-info__tier').find('b').string
            tier = re.match(r'.*(\d)', tier)
            tier = tier.groups()[0]
            position_tier[p] = int(tier)

            # Campeones contra los que es débil el campeón "c" según la posición
            counter_champs_html = champ_info.find_all(
                'table', class_='champion-stats-header-matchup__table')[0].find_all('tr')
            counter_champs = []
            for ch in counter_champs_html:
                counter_champs.append(ch.find(
                    'td', class_='champion-stats-header-matchup__table__champion').text.replace('\n', '').replace('\t', ''))
            position_counters_champs[p] = counter_champs

            # Campeones contra los que es fuerte el campeón "c" según la posición
            strong_against_champs = champ_info.find_all(
                'table', class_='champion-stats-header-matchup__table')[1].find_all('tr')
            strong_against = []
            for ch in strong_against_champs:
                strong_against.append(ch.find(
                    'td', class_='champion-stats-header-matchup__table__champion').text.replace('\n', '').replace('\t', ''))
            position_strong_against_champs[p] = strong_against

            # Winrate según la posición
            champ_info_body = parser3.find('div', class_='champion-box--trend')
            winrate = float(champ_info_body.find(
                'div', class_='champion-stats-trend-rate').string.strip().replace('%', ''))
            position_winrate[p] = winrate

        # Se guarda un diccionario relacionado con cada nombre y otro diccionario de tier, counters, strongs y winrate según la posición
        name_position_tier[champ_name] = position_tier
        name_position_counters_champs[champ_name] = position_counters_champs
        name_position_strong_against_champs[champ_name] = position_strong_against_champs
        name_position_winrate[champ_name] = position_winrate

        # Añadimos los campeones al esquema de campeones
        writer1.add_document(idChampion=count_champion, name=str(champ_name), image=str(
            champ_image), releaseDate=name_release_date[str(champ_name)])
        count_champion = count_champion + 1

    print('Se han indexado ' + str(count_champion-1) + ' campeones')
    print('Se han indexado ' + str(count_skill-1) + ' habilidades')
    writer1.commit()
    writer2.commit()

    # Añadimos los niveles al esquema de niveles
    # En idsChampionCounter e idsChampionStronger se guardan en string separado por comas las ids de los campeones
    ix_champs = open_dir(champions_directory)
    ix_positions = open_dir(positions_directory)
    count_tier = 1
    with ix_champs.searcher() as searcher_champs:
        doc_champs = searcher_champs.documents()
        for dc in doc_champs:
            position_tier = name_position_tier[dc['name']]
            for p in position_tier.keys():  # En p tengo la posición (Mid, Top, etc) que tenga el campeón
                position_counters_champs = name_position_counters_champs[dc['name']]
                position_strong_against_champs = name_position_strong_against_champs[dc['name']]
                position_winrate = name_position_winrate[dc['name']]
                ids_champions_counters = []
                ids_champions_strongers = []
                for pcc in position_counters_champs[p]:
                    query = QueryParser(
                        'name', ix_champs.schema).parse(str(pcc))
                    doc_champs_results = searcher_champs.search(query)
                    ids_champions_counters.append(
                        str(doc_champs_results[0]['idChampion']))
                for psac in position_strong_against_champs[p]:
                    query = QueryParser(
                        'name', ix_champs.schema).parse(str(psac))
                    doc_champs_results = searcher_champs.search(query)
                    ids_champions_strongers.append(
                        str(doc_champs_results[0]['idChampion']))
                seperator = ', '
                ids_champions_counters = seperator.join(ids_champions_counters)
                ids_champions_strongers = seperator.join(
                    ids_champions_strongers)
                with ix_positions.searcher() as searcher_positions:
                    query = QueryParser(
                        'name', ix_positions.schema).parse(str(p))
                    doc_positions_results = searcher_positions.search(query)
                    writer4.add_document(idTier=count_tier, level=position_tier[p], idChampion=name_id_champ[dc['name']], idPosition=doc_positions_results[
                                         0]['idPosition'], idsChampionCounter=ids_champions_counters, idsChampionStronger=ids_champions_strongers, winrate=position_winrate[p])
                    count_tier = count_tier + 1
    writer4.commit()
    print('Se han indexado ' + str(count_tier-1) +
          ' niveles según la posición del campeón')


def getPlayerInfo():
    main_directory = 'info_champ'
    players_directory = main_directory + '/' + 'players'
    if not os.path.exists(main_directory):
        os.mkdir(main_directory)
    if not os.path.exists(players_directory):
        os.mkdir(players_directory)
    ix1 = create_in(players_directory, schema=schemaPlayers())
    writer1 = ix1.writer()
    page = 1
    limit = 1
    count_players = 1
    while(page <= limit):
        # Accedemos a la página
        url = 'https://euw.op.gg/ranking/ladder/page=' + str(page)
        file = urllib.request.urlopen(url)
        parser = BeautifulSoup(file, 'html.parser')
        # Sacar los datos de los más altos solo si es la primera página
        if page == 1:
            higher = parser.find_all('li', class_='ranking-highest__item')
            for h in higher:
                higher_name = h.find('a', class_='ranking-highest__name').text
                higher_url = h.find(
                    'a', class_='ranking-highest__name')['href']
                higher_url = 'https:' + higher_url
                ranking = h.find(
                    'div', class_='ranking-highest__tierrank').find('span').text.strip()
                winrate = h.find('span', class_='winratio__text').text
                winrate = int(winrate.replace('%', ''))

                # Se accede a su url y se sacan sus campeones jugados
                file2 = urllib.request.urlopen(higher_url)
                parser2 = BeautifulSoup(file2, 'html.parser')
                champs = parser2.find_all('div', class_='GameItemWrap')
                champ_list_id = []

                # Se iteran los campeones y por cada uno se coge su id y se almacena en la lista
                for champ in champs:
                    champ_name = champ.find(
                        'div', class_='ChampionName').text.strip()
                    # Llamada al método para recuperar el id
                    id_champ = getIdByChampionName(champ_name)
                    champ_list_id.append(str(id_champ))
                seperator = ', '
                champ_list_id = seperator.join(champ_list_id)
                # Se guarda el jugador
                writer1.add_document(idPlayer=count_players, name=higher_name, urlPerfil=higher_url,
                                     ranking=ranking, winrate=winrate, idsChampion=champ_list_id)
                # Se incrementa el id del jugador
                count_players = count_players + 1

        # Se sacan el resto de jugadores
        normal_table = parser.find_all('tr', class_='ranking-table__row')
        for row in normal_table:
            normal_name = row.find(
                'td', class_='select_summoner ranking-table__cell ranking-table__cell--summoner').find('span').text
            normal_url = row.find(
                'td', class_='select_summoner ranking-table__cell ranking-table__cell--summoner').find('a')['href']
            normal_url = 'https:' + normal_url
            normal_ranking = row.find(
                'td', class_='ranking-table__cell ranking-table__cell--tier').text.strip()
            normal_winrate = row.find(
                'span', class_='winratio__text').text.strip()
            normal_winrate = int(normal_winrate.replace('%', ''))
            # Se accede a su url y se sacan sus campeones jugados
            file2 = urllib.request.urlopen(higher_url)
            parser2 = BeautifulSoup(file2, 'html.parser')
            champs = parser2.find_all('div', class_='GameItemWrap')
            champ_list_id = []
            # Se iteran los campeones y por cada uno se coge su id y se almacena en la lista
            for champ in champs:
                champ_name = champ.find(
                    'div', class_='ChampionName').text.strip()
                champ_list_id = []
                # Llamada al método para recuperar el id
                id_champ = getIdByChampionName(champ_name)
                champ_list_id.append(str(id_champ))
            seperator = ', '
            champ_list_id = seperator.join(champ_list_id)
            # Se guarda el jugador
            writer1.add_document(idPlayer=count_players, name=normal_name, urlPerfil=normal_url,
                                 ranking=normal_ranking, winrate=normal_winrate, idsChampion=champ_list_id)
            # Se incrementa el id del jugador
            count_players = count_players + 1
        # Se incrementa para acceder a la siguiente página
        page = page + 1
    writer1.commit()
    print('Se han indexado ' + str(count_players-1) + ' jugadores')


def schemaChampions():
    schema = Schema(idChampion=NUMERIC(stored=True),
                    name=TEXT(stored=True),
                    image=TEXT(stored=True),
                    releaseDate=DATETIME(stored=True))
    return schema


def schemaSkill():
    schema = Schema(idSkill=NUMERIC(stored=True),
                    name=TEXT(stored=True),
                    description=TEXT(stored=True),
                    video=TEXT(stored=True),
                    idChampion=NUMERIC(stored=True))
    return schema


def schemaPosition():
    schema = Schema(idPosition=NUMERIC(stored=True),
                    name=TEXT(stored=True))
    return schema


def schemaTier():
    schema = Schema(idTier=NUMERIC(stored=True),
                    level=NUMERIC(stored=True),
                    idChampion=NUMERIC(stored=True),
                    idPosition=NUMERIC(stored=True),
                    idsChampionCounter=TEXT(stored=True),
                    idsChampionStronger=TEXT(stored=True),
                    winrate=NUMERIC(stored=True, decimal_places=2))
    return schema


def schemaPlayers():
    schema = Schema(idPlayer=NUMERIC(stored=True),
                    name=TEXT(stored=True),
                    urlPerfil=TEXT(stored=True),
                    ranking=TEXT(stored=True),
                    winrate=NUMERIC(stored=True),
                    idsChampion=TEXT(stored=True))
    return schema


def populate(request):
    print("---------------------------------------------------------")
    populate_champion()
    populate_player()
    populate_position()
    populate_skill()
    populate_tier()
    return render(request, 'index.html', {'STATIC_URL': settings.STATIC_URL})


def populateWhoosh(request):
    print("---------------------------------------------------------")
    getChampsInfo()
    getPlayerInfo()
    return render(request, 'index.html', {'STATIC_URL': settings.STATIC_URL})


def populate_champion():
    print("Loading champions...")
    Champion.objects.all().delete()
    main_directory = 'info_champ'
    champions_directory = main_directory + '/' + 'champions'
    lista = []
    ix = open_dir(champions_directory)
    with ix.searcher() as searcher:
        doc = searcher.documents()
        for row in doc:
            lista.append(Champion(
                idChampion=row['idChampion'], name=row['name'], image=row['image'], releaseDate=row['releaseDate']))
    Champion.objects.bulk_create(lista)
    print("Champion inserted: " + str(Champion.objects.count()))
    print("---------------------------------------------------------")


def populate_position():
    print("Loading position...")
    Position.objects.all().delete()
    main_directory = 'info_champ'
    directory = main_directory + '/' + 'positions'
    lista = []
    ix = open_dir(directory)
    with ix.searcher() as searcher:
        doc = searcher.documents()
        for row in doc:
            lista.append(
                Position(idPosition=row['idPosition'], name=row['name']))
    Position.objects.bulk_create(lista)
    print("Position inserted: " + str(Position.objects.count()))
    print("---------------------------------------------------------")


def populate_skill():
    print("Loading skill...")
    Skill.objects.all().delete()
    main_directory = 'info_champ'
    directory = main_directory + '/' + 'skills'
    lista = []
    ix = open_dir(directory)
    with ix.searcher() as searcher:
        doc = searcher.documents()
        for row in doc:
            champion = Champion.objects.get(idChampion=row['idChampion'])
            lista.append(Skill(idSkill=row['idSkill'], name=row['name'],
                               description=row['description'], video=row['video'], champion=champion))
    Skill.objects.bulk_create(lista)
    print("Skill inserted: " + str(Skill.objects.count()))
    print("---------------------------------------------------------")


def populate_player():
    print("Loading player...")
    Player.objects.all().delete()
    main_directory = 'info_champ'
    directory = main_directory + '/' + 'players'
    lista = []
    ix = open_dir(directory)
    with ix.searcher() as searcher:
        doc = searcher.documents()
        for row in doc:
            p = Player(idPlayer=row['idPlayer'], name=row['name'],
                       urlPerfil=row['urlPerfil'], ranking=row['ranking'], winrate=row['winrate'])
            listChampion = []
            for id in row['idsChampion'].split(','):
                champion = Champion.objects.get(idChampion=id)
                listChampion.append(champion)
            p.save()
            p.idsChampion.set(listChampion)
            lista.append(p)
    print("Player inserted: " + str(Player.objects.count()))
    print("---------------------------------------------------------")


def populate_tier():
    print("Loading Tier...")
    Tier.objects.all().delete()
    main_directory = 'info_champ'
    directory = main_directory + '/' + 'tiers'
    lista = []
    ix = open_dir(directory)
    with ix.searcher() as searcher:
        doc = searcher.documents()
        for row in doc:
            champion = Champion.objects.get(idChampion=row['idChampion'])
            position = Position.objects.get(idPosition=row['idPosition'])
            p = Tier(idTier=row['idTier'],
                     level=row['level'],
                     winrate=row['winrate'], idChampion=champion, idPosition=position)
            ids_champion_counter_list = []
            for id in row['idsChampionCounter'].split(','):
                champion = Champion.objects.get(idChampion=id)
                ids_champion_counter_list.append(champion)
            ids_champion_stronger_list = []
            for id in row['idsChampionStronger'].split(','):
                champion = Champion.objects.get(idChampion=id)
                ids_champion_stronger_list.append(champion)
            p.save()
            p.idsChampionCounter.set(ids_champion_counter_list)
            p.idsChampionStronger.set(ids_champion_stronger_list)
            lista.append(p)
    print("Tier inserted: " + str(Tier.objects.count()))
    print("---------------------------------------------------------")


def getIdByChampionName(champ_name):
    main_directory = 'info_champ'
    champions_directory = main_directory + '/' + 'champions'
    ix = open_dir(champions_directory)
    with ix.searcher() as searcher:
        entry = str(champ_name)
        query = QueryParser('name', ix.schema).parse(entry)
        results = searcher.search(query)
        row = results[0]
        id = row['idChampion']
    return id


def getChampionByName(request):
    formulario = ChampionBusquedaForm()
    campeones = None
    skills = None
    tiers = None
    positions = []
    if request.method == 'POST':
        formulario = ChampionBusquedaForm(request.POST)

        if formulario.is_valid():
            campeones = Champion.objects.filter(
                name=formulario.cleaned_data['champion_name'])
            for champ in campeones:
                skills = Skill.objects.filter(champion=champ.idChampion)
                tiers = Tier.objects.filter(idChampion=champ.idChampion)
                for tie in tiers:
                    positions.append(Position.objects.get(name=tie.idPosition))
    return render(request, 'busqueda_champions.html', {'formulario': formulario, 'campeones': campeones, 'skills': skills, 'positions': positions, 'STATIC_URL': settings.STATIC_URL})


def getPlayerByName(request):
    formulario = PlayerBusquedaForm()
    jugadores = None
    if request.method == 'POST':
        formulario = PlayerBusquedaForm(request.POST)

        if formulario.is_valid():
            jugadores = Player.objects.filter(
                name=formulario.cleaned_data['player_name'])
    return render(request, 'busqueda_players.html', {'formulario': formulario, 'jugadores': jugadores, 'STATIC_URL': settings.STATIC_URL})

def getChampionByRangeDates(request):
    formulario = ChampionDatesBusquedaForm()
    campeones = None
    skills = None
    tiers = None
    positions = []
    if request.method == 'POST':
        formulario = ChampionDatesBusquedaForm(request.POST)
        if formulario.is_valid():
            campeones = Champion.objects.filter(releaseDate__range=(formulario.cleaned_data['startDate'], formulario.cleaned_data['endDate'])).order_by('releaseDate')
    return render(request, 'busqueda_champions_fechas.html', {'formulario': formulario, 'campeones': campeones, 'STATIC_URL': settings.STATIC_URL})



def list_campeones(request):
    campeones = Champion.objects.all().order_by('name')
    return render(request, 'list_campeones.html', {'campeones': campeones, 'STATIC_URL': settings.STATIC_URL})


def list_jugadores(request):
    jugadores = Player.objects.all().order_by('name')
    return render(request, 'list_jugadores.html', {'jugadores': jugadores, 'STATIC_URL': settings.STATIC_URL})


def mejores_campeones(request):
    idChampions = Tier.objects.filter(idPosition_id=1).annotate(avg_rating=Avg(
        'winrate')).order_by('-avg_rating').values('idChampion', 'winrate')[:3]
    campeones_bot_winrate = {}
    for id in idChampions:
        champ = Champion.objects.get(idChampion=id['idChampion'])
        campeones_bot_winrate[champ] = id['winrate']

    idChampions = Tier.objects.filter(idPosition_id=2).annotate(avg_rating=Avg(
        'winrate')).order_by('-avg_rating').values('idChampion', 'winrate')[:3]
    campeones_mid_winrate = {}
    for id in idChampions:
        champ = Champion.objects.get(idChampion=id['idChampion'])
        campeones_mid_winrate[champ] = id['winrate']

    idChampions = Tier.objects.filter(idPosition_id=3).annotate(avg_rating=Avg(
        'winrate')).order_by('-avg_rating').values('idChampion', 'winrate')[:3]
    campeones_jungle_winrate = {}
    for id in idChampions:
        champ = Champion.objects.get(idChampion=id['idChampion'])
        campeones_jungle_winrate[champ] = id['winrate']

    idChampions = Tier.objects.filter(idPosition_id=4).annotate(avg_rating=Avg(
        'winrate')).order_by('-avg_rating').values('idChampion', 'winrate')[:3]
    campeones_top_winrate = {}
    for id in idChampions:
        champ = Champion.objects.get(idChampion=id['idChampion'])
        campeones_top_winrate[champ] = id['winrate']

    idChampions = Tier.objects.filter(idPosition_id=5).annotate(avg_rating=Avg(
        'winrate')).order_by('-avg_rating').values('idChampion', 'winrate')[:3]
    campeones_support_winrate = {}
    for id in idChampions:
        champ = Champion.objects.get(idChampion=id['idChampion'])
        campeones_support_winrate[champ] = id['winrate']

    idChampions = Tier.objects.annotate(avg_rating=Avg('winrate')).order_by(
        '-avg_rating').values('idChampion', 'winrate')[:3]
    campeones_winrate = {}
    for id in idChampions:
        champ = Champion.objects.get(idChampion=id['idChampion'])
        campeones_winrate[champ] = id['winrate']

    return render(request, 'mejores_campeones.html', {'campeones': campeones_winrate, 'campeones_bot': campeones_bot_winrate, 'campeones_mid': campeones_mid_winrate, 'campeones_jungle': campeones_jungle_winrate, 'campeones_top': campeones_top_winrate, 'campeones_support': campeones_support_winrate,
                                                      'STATIC_URL': settings.STATIC_URL})


def counterestChamps(request):
    idChampions = Tier.objects.values('idsChampionCounter')

    campeones = []
    for id in idChampions:
        campeones.append(id['idsChampionCounter'])
    result = Counter(campeones).most_common()[:5]
    cam = []
    for r in result:
        cam.append(r[0])
    campeones = []
    for id in cam:
        campeones.append(Champion.objects.get(idChampion=id))

    return render(request, 'list_campeones.html', {'campeones': campeones, 'STATIC_URL': settings.STATIC_URL})


def weakChamps(request):
    idChampions = Tier.objects.values('idsChampionStronger')

    campeones = []
    for id in idChampions:
        campeones.append(id['idsChampionStronger'])
    result = Counter(campeones).most_common()[:5]
    repet = result[0][1]
    cam = []
    for r in result:
        cam.append(r[0])
    campeones = []
    for id in cam:
        campeones.append(Champion.objects.get(idChampion=id))

    return render(request, 'list_campeones.html', {'campeones': campeones, 'STATIC_URL': settings.STATIC_URL})


def mejores_jugadores(request):
    jugadores = Player.objects.annotate(
        avg_rating=Avg('winrate')).order_by('-avg_rating')[:3]
    return render(request, 'list_jugadores.html', {'jugadores': jugadores, 'STATIC_URL': settings.STATIC_URL})


def list_campeones_por_posicion(request):
    formulario = PositionBusquedaForm()
    campeones = None

    if request.method == 'POST':
        formulario = PositionBusquedaForm(request.POST)

        if formulario.is_valid():
            data = formulario.cleaned_data['positionName']
            pos = ['Top', 'Bot', 'Support', 'Jungle', 'Mid']
            if data in pos:
                idPosition = Position.objects.get(
                    name=formulario.cleaned_data['positionName'])
                idChampions = Tier.objects.filter(
                    idPosition_id=idPosition).values('idChampion').order_by('idChampion')
                campeones = []
                for id in idChampions:
                    campeones.append(Champion.objects.get(
                        idChampion=id['idChampion']))

    return render(request, 'campeones_posicion.html', {'campeones': campeones, 'STATIC_URL': settings.STATIC_URL})


def list_campeones_por_posicion_tier(request):
    formulario = PositionTierBusquedaForm()
    campeones = None

    if request.method == 'POST':
        formulario = PositionTierBusquedaForm(request.POST)

        if formulario.is_valid():
            data = formulario.cleaned_data['positionName']
            pos = ['Top', 'Bot', 'Support', 'Jungle', 'Mid']
            if data in pos:
                idPosition = Position.objects.get(
                    name=formulario.cleaned_data['positionName'])
                idChampions = Tier.objects.filter(
                    idPosition_id=idPosition, level=formulario.cleaned_data['level']).values('idChampion')
                campeones = []
                for id in idChampions:
                    campeones.append(Champion.objects.get(
                        idChampion=id['idChampion']))

    return render(request, 'buscar_camp_pos_lev.html', {'campeones': campeones, 'STATIC_URL': settings.STATIC_URL})



def recomendacionChampion(request):
    formulario = ChampionBusquedaForm()
    campeones = None
    dat= []
    champDat = []
    datos = {}
    if request.method=='POST':
        formulario = ChampionBusquedaForm(request.POST)
        
        if formulario.is_valid():
            campeones = Champion.objects.all()
            for champ in campeones:
                tiers = Tier.objects.filter(idChampion = champ.idChampion)
                for tie in tiers:
                    position = Position.objects.get(name = tie.idPosition)
                    actual = 'l'+str(tie.level) + ' ' + position.name + ' ' + 'w'+str(tie.winrate)
                    name = champ.name
                    if name in champDat:
                        anterior = datos.get(name)
                        upgrade = actual+ ' ' + anterior
                        datos.update({name: upgrade})
                        dat.append(actual)
                    else:    
                        datos.update({ name: actual})
                        champDat.append(name)
            values = datos.values()
            values = list(values)
           
            d = {'Nombre': champDat , 'Valores' : values}
            df = pd.DataFrame(data = d , index = champDat)
            df = df[['Nombre','Valores']]

            df.head()
            df['Key_words'] = ""
            for index, row in df.iterrows():

                valor = row['Valores']
                r = Rake()
                r.extract_keywords_from_text(valor)
                key_words_dict_scores = r.get_word_degrees()
                row['Key_words'] = str(list(key_words_dict_scores.keys()))
            df.drop(columns = ['Valores'], inplace = True)

            count = CountVectorizer()
            count_matrix = count.fit_transform(df['Key_words'])
            
                
            cosine_sim = cosine_similarity(count_matrix, count_matrix)
            indices = pd.Series(df.index)
            recommended_champs = []
            champion_name =formulario.cleaned_data['champion_name']

            idx = indices[indices == champion_name ].index[0]
            score_series = pd.Series(cosine_sim[idx]).sort_values(ascending = False)

            top_10_indexes = list(score_series.iloc[1:11].index)

            for i in top_10_indexes:

                recommended_champs.append(list(df.index)[i])
            campeones = []            
            for name_c in recommended_champs:
                campeones.append(Champion.objects.get(name=name_c))
    return render(request, 'campeones_recomendados.html', {'campeones': campeones, 'STATIC_URL': settings.STATIC_URL})


def recomendacionPlayer(request):
    formulario = PlayerBusquedaForm()
    jugadores = None
    dat= []
    playerDat = []
    datos = {}
    if request.method=='POST':
        formulario = PlayerBusquedaForm(request.POST)
        
        if formulario.is_valid():
            jugadores = Player.objects.all()
            for player in jugadores:
                idsChampions = player.idsChampion.all()
                name_p = player.name
                for champ in idsChampions:
                    name_player = player.name
                    actual = []
                    actual.append(champ.name)
                datos.update({name_player : (str(actual) + ' w' + str(player.winrate))})
                playerDat.append(name_p)
            values = datos.values()
            values = list(values)
           
            d = {'Nombre': playerDat , 'Valores' : values}
            df = pd.DataFrame(data = d , index = playerDat)
            df = df[['Nombre','Valores']]

            df.head()
            df['Key_words'] = ""
            for index, row in df.iterrows():

                valor = row['Valores']
                r = Rake()
                r.extract_keywords_from_text(valor)
                key_words_dict_scores = r.get_word_degrees()
                row['Key_words'] = str(list(key_words_dict_scores.keys()))
            df.drop(columns = ['Valores'], inplace = True)

            count = CountVectorizer()
            count_matrix = count.fit_transform(df['Key_words'])
            
                
            cosine_sim = cosine_similarity(count_matrix, count_matrix)
            indices = pd.Series(df.index)
            recommended_player = []
            player_name =formulario.cleaned_data['player_name']

            idx = indices[indices == player_name ].index[0]
            score_series = pd.Series(cosine_sim[idx]).sort_values(ascending = False)

            top_10_indexes = list(score_series.iloc[1:11].index)

            for i in top_10_indexes:

                recommended_player.append(list(df.index)[i])
            jugadores = []            
            for name_c in recommended_player:
                jugadores.append(Player.objects.get(name=name_c))
    return render(request, 'jugadores_recomendados.html', {'jugadores': jugadores, 'STATIC_URL': settings.STATIC_URL})
