import re

import urllib.request
import re
import os
from bs4 import BeautifulSoup
from django.shortcuts import render

#from main.models import Champion, Position, Skill, Tier
from whoosh import qparser
from whoosh.fields import DATETIME, TEXT, ID, NUMERIC, Schema
from whoosh.index import create_in, open_dir
from whoosh.qparser import MultifieldParser, QueryParser


def getChampsInfo(directorioDestino1, directorioDestino2, directorioDestino3, directorioDestino4):
    if not os.path.exists(directorioDestino1):
        os.mkdir(directorioDestino1)
    if not os.path.exists(directorioDestino2):
        os.mkdir(directorioDestino2)
    if not os.path.exists(directorioDestino3):
        os.mkdir(directorioDestino3)
    if not os.path.exists(directorioDestino4):
        os.mkdir(directorioDestino4)
    ix1 = create_in(directorioDestino1, schema=schemaChampions())
    ix2 = create_in(directorioDestino2, schema=schemaSkill())
    ix3 = create_in(directorioDestino3, schema=schemaPosition())
    ix4 = create_in(directorioDestino4, schema=schemaTier())
    writer1 = ix1.writer()
    writer2 = ix2.writer()
    writer3 = ix3.writer()
    writer4 = ix4.writer()
    count_champion = 1
    url = 'https://euw.op.gg/champion/statistics'
    file = urllib.request.urlopen(url)
    parser = BeautifulSoup(file, 'html.parser')
    items = parser.find_all(lambda tag: tag.name == 'div' and 'champion-index__champion-item' in tag.get(
        'class') and 'tip' not in tag.get('class'))
    for i in items:
        champ_stadics = i.find('a')['href']
        champ_stadics = 'https://euw.op.gg/' + champ_stadics
        file2 = urllib.request.urlopen(champ_stadics)
        parser2 = BeautifulSoup(file2, 'html.parser')
        champ_info = parser2.find('div', class_='l-champion-statistics-header')
        name = champ_info.find(
            'h1', class_='champion-stats-header-info__name').string
        image = champ_info.find(
            'div', class_='champion-stats-header-info__image').find('img')['src']

        writer1.add_document(idChampion= count_champion , name=name, image=image)    
        # Skilless
        skills = champ_info.find_all('div', class_='champion-stat__skill')
        for s in skills:
            html_skill = s['title']
            html_skill = html_skill.replace('<br>', '\n').replace(
                '<br/>', '\n').replace('<br />', '\n')
            parser_skill = BeautifulSoup(html_skill, 'html.parser')
            skill_name = parser_skill.find('b').string
            skill_description = parser_skill.find(
                lambda tag: tag.name == 'span' and not tag.attrs)
            if skill_description is None:
                skill_description = ''
            else:
                skill_description = skill_description.text
            skill_video = s.find('a')['href']
            writer2.add_document(name=skill_name, description=skill_description,
                                 video=skill_video, idChampion=count_champion)
        print('indexado skills')
        # Las positions
        positions = champ_info.find_all(
            'li', class_='champion-stats-header__position')
        position_list = []
        for p in positions:
            position_list.append(
                p.find('span', class_='champion-stats-header__position__role').string)
        position_tier = {}
        position_counters_champs = {}
        position_strong_against_champs = {}
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
            tier = champ_info.find(
                'div', class_='champion-stats-header-info__tier').find('b').string
            tier = re.match(r'.*(\d)', tier)
            tier = tier.groups()[0]
            position_tier[p] = int(tier)

            # Counter y otras vainas
            counter_champs_html = champ_info.find_all(
                'table', class_='champion-stats-header-matchup__table')[0].find_all('tr')
            counter_champs = []
            for ch in counter_champs_html:
                counter_champs.append(ch.find(
                    'td', class_='champion-stats-header-matchup__table__champion').text.replace('\n', '').replace('\t', ''))
            position_counters_champs[p] = counter_champs
            strong_against_champs = champ_info.find_all(
                'table', class_='champion-stats-header-matchup__table')[1].find_all('tr')
            strong_against = []
            for ch in strong_against_champs:
                strong_against.append(ch.find(
                    'td', class_='champion-stats-header-matchup__table__champion').text.replace('\n', '').replace('\t', ''))
            position_strong_against_champs[p] = strong_against
        print('vamos por las tier')
        for key in position_tier.keys():
            if key == 'Middle':
                id_position = 2
            if key == 'Bottom':
                id_position = 1
            if key == 'Jungle':
                id_position = 3
            if key == 'Top':
                id_position = 4
            if key == 'Support':
                id_position = 5
            writer4.add_document(rating=position_tier[key], idChampion=count_champion, idPosition=id_position,
                                 idChampionCounter=str(position_counters_champs[key]), idChampionStronger=str(position_strong_against_champs[key]))
       
        
        print('Se han indexado el campeon ' + name + ' ' + 'número ' + count_champion)
        count_champion = count_champion + 1
 

    writer3.add_document(idPosition=1, name='Bot')
    writer3.add_document(idPosition=2, name='Mid')
    writer3.add_document(idPosition=3, name='Jungle')
    writer3.add_document(idPosition=4, name='Top')
    writer3.add_document(idPosition=5, name='Support')
    # Nombre del campeón -> string
    # Nombre de variable -> name
    # Imagen del campeón -> string
    # Nombre de variable -> image
    # Habilidades del campeón -> Diccionario {string, list} -> {nombre de la skill, [descripción, video]} #Debe haber siempre 5 skills
    # Nombre de variable -> skill_list
    # Tier según posición -> Diccionario {string, string} -> {posición, numero del tier}
    # Nombre de variable -> position_level
    # Campeones counters según posición -> Diccionario {string, list} -> {posición, [string, string, string]}
    # Nombre de variable -> position_counters_champs
    # Campeones fuertes contra según posición -> Diccionario {string, list} -> {posición, [string, string, string]}
    # Nombre de variable -> position_strong_against_champs


def schemaChampions():
    schema = Schema(idChampion=NUMERIC(stored=True),
                    name=TEXT(stored=True),
                    image=TEXT(stored=True))
    return schema


def schemaSkill():
    schema = Schema(name=TEXT(stored=True),
                    description=TEXT(stored=True),
                    video=TEXT(stored=True),
                    idChampion=NUMERIC(stored=True))
    return schema


def schemaPosition():
    schema = Schema(idPosition=NUMERIC(stored=True),
                    name=TEXT(stored=True))
    return schema


def schemaTier():
    schema = Schema(rating=NUMERIC(stored=True),
                    idChampion=NUMERIC(stored=True),
                    idPosition=NUMERIC(stored=True),
                    idChampionCounter=TEXT(stored=True),
                    idChampionStronger=TEXT(stored=True))
    return schema


getChampsInfo('champion', 'skills', 'position', 'tier')
