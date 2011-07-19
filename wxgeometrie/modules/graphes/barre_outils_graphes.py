# -*- coding: iso-8859-1 -*-
from __future__ import division # 1/2 == .5 (par defaut, 1/2 == 0)

##--------------------------------------##
#               Barre d'outils pour la g�om�trie               #
##--------------------------------------##
#    WxGeometrie
#    Dynamic geometry, graph plotter, and more for french mathematic teachers.
#    Copyright (C) 2005-2010  Nicolas Pourcelot
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

#from LIB import *
#from GUI.wxlib import png
from ...GUI.barre_outils import BarreOutils
from ...geolib import Arc_oriente, Arc_points, Point_generique


class BarreOutilsGraphes(BarreOutils):
    def __init__(self, parent, couleur = None):
        BarreOutils.__init__(self, parent, couleur)


    def creer_boutons(self):
        self.add("F1", (u"Pointeur", u"fleche4", u"D�placer ou modifier un objet.", self.curseur),
                  (u"Zoomer", u"zoombox2", u"Recentrer la zone d'affichage.", self.zoombox),
                  (u"S�lectionner", u"selection", u"S�lectionner une partie de la feuille.",
                  self.selectionner)).display(True)
        self.add("F2", (u"Sommet", u"point2",u"Cr�er un point.", self.point))
        self.add("F3", (u"Ar�te", u"segment2", u"Cr�er une ar�te droite.", self.segment))
        self.add("F4", (u"Ar�te orient�e", u"vecteur", u"Cr�er une ar�te orient�e droite.", self.vecteur),
                    )
        self.add("F5", (u"Ar�te courbe", u"arc_points",
                    u"Cr�er une ar�te courbe (d�finir 3 points).", self.arc_points),
                    )
        self.add("F6", (u"Ar�te orient�e (courbe)", u"arc_oriente",
                    u"Cr�er une ar�te orient�e courbe (d�finir 3 points).", self.arc_oriente),
                    )
        self.add("F7", (u"Texte", u"texte", u"Cr�er un texte.", self.texte))
        self.add("F8", (u"Masquer", u"masquer", u"Masquer des objets.", self.masque))
        self.add("F9", (u"Gommer", u"gomme", u"Supprimer des objets.", self.gomme))
        self.add("Shift+F2", (u"Copier", u"pinceau", u"Copier le style d'un objet.", self.pinceau))




    def arc_points(self, event = False, **kw):
        if event is False:
            self.arc(Arc_points, nom_style='arc', **kw)
        else:
            self.interagir(self.arc_points, u"Choisissez ou cr�ez 3 points.")

    def arc_oriente(self, event = False, **kw):
        if event is False:
            self.arc(Arc_oriente, nom_style='arcs_orientes', **kw)
        else:
            self.interagir(self.arc_oriente, u"Choisissez ou cr�ez 3 points.")


    def arc(self, classe, nom_style = '', **kw):
        u"Cr�ation d'un arc d�fini par 3 points. Un style sp�cial est appliqu� au point interm�daire."
        if self.test(True, **kw):
            self.cache = [obj for obj in self.cache if obj.nom and obj.__feuille__ is self.feuille_actuelle]
            selection = kw["selection"]

            n = len(self.cache)

            if n == 1:
                # Le point interm�diaire a un style diff�rent,
                # et ne doit donc pas co�ncider avec un point d�j� existant.
                point = self.point(nom_style='points_ancrage', editer=None, **kw)
                self.cache.append(point)
                style = self.style(nom_style)
                style["previsualisation"] = True
                self.feuille_actuelle.objet_temporaire(classe(*(tuple(self.cache) + (self.feuille_actuelle.point_temporaire(),)), **style))
            elif isinstance(selection, Point_generique):
                self.cache.append(selection)
                nouveau_point = False
            else:
                self.cache.append(self.point(**kw))
                nouveau_point = True

            if n == 2:
                self.feuille_actuelle.objet_temporaire(None)
                code = classe.__name__ + "(" + ",".join(obj.nom for obj in self.cache) + ", **%s)" %self.style(nom_style)
                if nouveau_point: # on edite le nom du nouveau point (dernier parametre de self.executer)
                    self.executer(code, editer = self.cache[-1])
                else: # si c'est un vieux point, pas besoin d'editer son nom
                    self.executer(code)

            elif n > 3: # ne se produit que si l'execution a plante...
                self.initialiser()

        elif self.cache:
            style = self.style(nom_style)
            style["previsualisation"] = True
            self.feuille_actuelle.objet_temporaire(classe(*(tuple(self.cache) + (self.feuille_actuelle.point_temporaire(),)), **style))
        else:
            self.feuille_actuelle.objet_temporaire(None)
