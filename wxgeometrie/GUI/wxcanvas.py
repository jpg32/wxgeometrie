# -*- coding: iso-8859-1 -*-
from __future__ import division # 1/2 == .5 (par defaut, 1/2 == 0)
from __future__ import with_statement

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

import re
import wx
from numpy import array
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg

from ..API.canvas import Canvas
from .proprietes_objets import Proprietes
from .wxlib import PseudoEvent, BusyCursor
from .. import param
from ..pylib import print_error, debug
from ..geolib.textes import Texte, Texte_generique
from ..geolib.objet import Objet
from ..geolib.points import Point_generique
from ..geolib.constantes import NOM, FORMULE, TEXTE, RIEN

class MiniEditeur:
    def __init__(self, parent):
        self.parent = parent
        self.objet = None


    def init(self, objet, mode = 0):
        u"""Edition d'un nouvel objet.
        mode = 0: �dition du nom de l'objet
        mode = 1: �dition de l'�tiquette de l'objet"""
        self.close() # finalise l'�ventuelle �dition en cours
        self.texte = ""
        self.objet = objet
#        self.old_label = objet.label()
        self.mode = mode #
        self.display()

    def display(self):
        self.objet.label_temporaire = self.texte

    def cancel(self):
        self.objet.label_temporaire = None
        self.objet = None


    def ok(self):
        canvas = self.parent
        panel = canvas.parent
        # NB: si aucun nom n'est rentr�, [ENTREE] est un �quivalent de [ECHAP].
        if self.texte:
            try: # si possible, on change le nom de l'objet ; sinon, on change son label.
                nom = self.objet.nom
                if isinstance(self.objet, Texte) or not re.match("""[A-Za-z_][A-Za-z0-9_'"`]*$""", self.texte):
                    self.mode = 1 # label
                if self.mode:
                    self.objet.label(self.texte)
                    panel.action_effectuee(u"%s.label(%s)" %(nom, repr(self.texte)))
                else:
                    self.objet.renommer(self.texte, legende = NOM)
                    panel.action_effectuee(u"%s.renommer(%s, legende = %s)" %(nom, repr(self.texte), NOM))
            except RuntimeError: # on reste en mode edition
                if not param.nom_multiple:
                    self.display()
                    raise
                self.objet.label(self.texte) # par d�faut, si A est r�attribu� � un point, il sera trait� comme �tiquette.
                panel.action_effectuee(u"%s.label(%s)" %(nom, repr(self.texte)))
                canvas.message(u"Attention : ce nom est d�j� attribu�.")
            except:
                self.display()
                raise
        self.cancel()


    def key(self, key):
        if self:
            if key == wx.WXK_BACK:
                self.texte = self.texte[:-1]
                self.display()
            elif key == wx.WXK_ESCAPE:
                self.cancel()
            elif key == wx.WXK_RETURN or key == wx.WXK_NUMPAD_ENTER:
                self.ok()
            elif key == 10: # Ctrl + Entree (� tester sous Linux !)
                self.texte += "\n"
                self.display()
            elif key >= 32 and key <= 255 and key <> wx.WXK_DELETE:
                key = unichr(key) # a-z, A-Z, 0-9 ou _
                self.texte += key
                self.display()

    def close(self):
        u"Ferme l'�diteur. Ne renvoie pas d'erreur s'il est d�j� ferm�."
        if self:
            try:
                self.ok()
            except:
                self.cancel()
                print_error()


    def __nonzero__(self):
        return self.objet is not None










class WxCanvas(FigureCanvasWxAgg, Canvas):
    def __init__(self, parent, fixe = False):
        u"Si fixe = True, l'utilisateur ne peut pas zoomer ou recadrer la fen�tre d'affichage avec la souris."

        self.parent = parent
        # initialisation dans cet ordre (self.figure doit �tre d�fini pour initialiser FigureCanvas)
        Canvas.__init__(self, couleur_fond = self.param("couleur_fond"))
        FigureCanvasWxAgg.__init__(self, parent, -1, self.figure)

        if param.plateforme == "Linux":
            self.SetSize(wx.Size(10, 10))
        elif param.plateforme == "Windows":
            self.SetWindowStyle(wx.WANTS_CHARS)
            self.Refresh()

        self.debut_zoom = None
        # Utilis� pour zoomer avec Ctrl + Clic gauche (contiendra la position initiale)
        self.debut_select = None
        # Utilis� pour s�lectionner simultan�ment plusieurs objets avec Alt + Clic gauche (pos. initiale)
        self.debut_shift = None
        # Utilis� pour translater le contenu de la fen�tre (position initiale)
        self.redetecter = True
        # Rechercher les objets � proximit� du pointeur

        self.select_memoire = None
        # Objet devant �tre prochainement s�lectionn� (en cas de "litige" entre 2 objets)
        self.etiquette_selectionnee = None # �tiquette couramment s�l�ctionn�e
        self.fixe = fixe
        self.interaction = None
        # Fonction � lancer au prochain clic de souris (au lieu des actions par d�faut)
        self.interaction_deplacement = None
        # Fonction � lancer au prochain d�placement de souris (au lieu des actions par d�faut)
        self.editeur = MiniEditeur(self) # edite les noms et etiquettes des points, textes, etc.

        # Param�tres temporaires d'affichage
        self._dessin_temporaire = False


        self.sel = []
        # Liste ordonn�e (pour la d�tection) des objets de la feuille actuelle.
        self.motion_event = None
        self.wheel_event_count = 0
        self.wheel_ctrl_event_count = 0

        self.Bind(wx.EVT_MOUSEWHEEL, self.EventOnWheel)
        self.Bind(wx.EVT_MOTION, self.EventOnMotion)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_CHAR, self.OnChar)
        #self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        self._pile_instructions = [] # instructions � ex�cuter lorsqu'aucune autre action n'est en cours. (Idle)
        self.Bind(wx.EVT_IDLE, self.OnIdle)

        timer=wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._actualiser_si_necessaire)
        timer.Start(150)



    @property
    def feuille_actuelle(self):
        return self.parent.feuille_actuelle

    def param(self, *args, **kw):
        return self.parent.param(*args, **kw)

    def message(self, txt, lieu = 0):
        self.parent.parent.parent.message(txt, lieu) # cf. geometrie.py

    def _curseur(self, sablier):
        if sablier:
            wx.BeginBusyCursor()
        else:
            wx.EndBusyCursor()
            if wx.Platform == '__WXMSW__':
                # Le curseur dispara�t sinon sous Windows !!
                wx.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))

    @property
    def dimensions(self):
        if self._dimensions is None:
            return self.GetSizeTuple()
        return self._dimensions


    def _affiche_module(self):
        u"Affichage sp�cifique au module en cours."
        self.parent._affiche()

    def exporter(self, *args, **kw):
        with BusyCursor():
            Canvas.exporter(self, *args, **kw)

#    Gestion des evenements (essentiellement la souris).
###############################

    def coordonnees(self, event, dx = 0, dy = 0):
        u"""Renvoie les coordonn�es correspondant � l'�v�nement, converties en coordonn�es de la feuille.
        Si [Maj] est enfonc�e, les coordonn�es sont arrondies � la graduation la plus proche.
        dx et dy correspondent au d�calage entre les coordonn�es de l'objet, et le point o� on l'a saisit.
        (Par exemple, un texte n'est pas forc�ment saisi au niveau de son point d'ancrage).
        """
        x, y = self.pix2coo(*event.GetPositionTuple())
        if event.ShiftDown() or self.grille_aimantee:
            a, b = self.gradu
            return a*round((x + dx)/a), b*round((y + dy)/b)
        else:
            return float(x + dx), float(y + dy)



    def interagir(self, fonction, aide = None, fonction_bis = None):
        u"""Permet l'interaction du canevas avec un module externe.

        A chaque clic de souris, la fonction indiqu�e est appel�e, avec
        un certains nombre de param�tres comme arguments :
        objet(s) � proximit�, position en coordonn�es et en pixels...

        Une aide est �ventuellement affich�e dans la barre d'�tat de la fen�tre principale.

        fonction_bis est �ventuellement utilis�e lors de chaque d�placement de la souris.
        Elle re�oit en argument la position en pixels uniquement (pour ne pas alourdir le traitement).

        Exemple de r�cup�ration des arguments :
        si un module appelle self.canvas.interagir(ma_fonction, u"Cliquez n'importe o�.", ma_2eme_fonction),
        le module doit d�finir :

        def ma_fonction(self, **kw):
            pixel = kw["pixel"]
            position = kw["position"]
            objet_selectionne = kw["selection"]
            autres_objets_a_proximite = kw["autres"]
            print u"clic!"

        def ma_2eme_fonction(self, **kw):
            pixel = kw["pixel"]
            print u"�a bouge !"

        """

        self.interaction = fonction
        self.interaction_deplacement = fonction_bis
        if fonction:
            self.SetCursor(wx.StockCursor(wx.CURSOR_QUESTION_ARROW))
        else:
            self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))
        if aide is not None:
            self.message(aide)


    def signal(self, event = None):
        if self.interaction:
            pixel = event.GetPositionTuple()
            self.detecter(pixel)
            self.interaction(selection = self.select, autres = self.selections, position = self.coordonnees(event), pixel = pixel)
            self.detecter(pixel) # XXX: toujours utile ?


    def deplacable(self, obj): # indique si un objet est deplacable
        return isinstance(obj, Objet) and obj._deplacable

    def pointable(self, obj): # indique si un objet possede des coordonnees
        return isinstance(obj, Objet) and obj._pointable


    def infos(self):
        self.message(self.select.info if self.select is not None else '')


    def detecter(self, position = None):
        u"""D�tecte les objets � proximit� de la position indiqu�e.
        Typiquement, on utilise self.detecter(event.GetPositionTuple())."""

        self.redetecter = False
        self.debut_zoom = None
        actuelle = self.feuille_actuelle # feuille courante

        if not self.affichage_gele:
            if position is None:
                position = self.ScreenToClient(wx.GetMousePosition())
            if param.afficher_coordonnees: # affichage des coordonnees dans la barre d'etat
                self.message(str(self.pix2coo(*position)), 1)
            elif param.afficher_pixels:
                # pour d�bogage
                self.message(str(position) + ' -> ' + str(self.pix2coo(*position)), 1)
            x, y = position
            # on place les objets 'modifiables' en premier (points libres, glisseurs, textes)
            self.sel = actuelle.liste_objets(tri = True)
            # liste des objets pres du pointeur de la souris :
            self.selections = []
            for obj in self.sel:
                try:
                    if obj.distance_inf(x, y, param.precision_selection):
                        self.selections.append(obj)
                except:
                    print_error()
                    self.message(u"Erreur: les coordonn�es de %s sont incalculables." %obj.nom)
            proximite = len(self.selections)
            if proximite:
                self.select = self.selections[0]
                if self.select_memoire and self.select_memoire in self.selections:
                    self.select = self.select_memoire
                if self.interaction:
                    self.SetCursor(wx.StockCursor(wx.CURSOR_QUESTION_ARROW))
                else:
                    if self.deplacable(self.select):
                        self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
                    else:
                        self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))
                self.infos()
            else:
                if self.interaction:
                    self.SetCursor(wx.StockCursor(wx.CURSOR_QUESTION_ARROW))
                else:
                    self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))
                self.message("")
                self.select = None
            self.selection_en_gras()


    def OnIdle(self, event):
        u"Instructions � ex�cuter si aucun processus n'est en cours."
        if self.parent.parent.parent.closing:
            # L'application est en train d'�tre arr�t�e.
            # Tous les �v�nements restant passent � la trappe...
            return
        if self.wheel_event_count != 0:
            try:
                self.OnWheel(self.wheel_event_count)
            finally:
                self.wheel_event_count = 0
        elif self.wheel_ctrl_event_count != 0:
            try:
                self.OnCtrlWheel(self.wheel_ctrl_event_count)
            finally:
                self.wheel_ctrl_event_count = 0
        elif self.motion_event is not None:
            try:
                self.OnMotion(self.motion_event)
            finally:
                self.motion_event = None
        elif self._pile_instructions:
            try:
                fonction, args, kwargs = self._pile_instructions[-1]
                fonction(*args, **kwargs)
            finally:
                self._pile_instructions.pop()
        self._actualiser_si_necessaire()


    def execute_on_idle(self, fonction, *args, **kwargs):
        u"Ex�cuter une fois qu'aucun processus n'est actif."
        self._pile_instructions.append((fonction, args, kwargs))

    def EventOnWheel(self, event):
        if event.ControlDown():
            if event.GetWheelRotation() > 0:
                self.wheel_ctrl_event_count += 1
            else:
                self.wheel_ctrl_event_count -= 1
        else:
            if event.GetWheelRotation() > 0:
                self.wheel_event_count += 1
            else:
                self.wheel_event_count -= 1


    def OnWheel(self, wheel_event_count):
        u"Gestion du zoom par la roulette de la souris."
        if self.fixe: return
        if wheel_event_count > 0:
            self.zoomer(param.zoom_in**wheel_event_count)
            self.parent.action_effectuee("zoom_in", signature = 'zoom_in')
#            self.zoom_in()
        else:
#            self.zoom_out()
            self.zoomer(param.zoom_out**(-wheel_event_count))
            self.parent.action_effectuee("zoom_out", signature = 'zoom_out')


    def OnCtrlWheel(self, wheel_ctrl_event_count):
        u"Gestion du zoom du texte par la roulette de la souris."
        if wheel_ctrl_event_count > 0:
            self.zoom_texte *= param.zoom_texte_in**wheel_ctrl_event_count
            self.zoom_ligne *= param.zoom_ligne_in**wheel_ctrl_event_count
        else:
            self.zoom_texte *= param.zoom_texte_out**(-wheel_ctrl_event_count)
            self.zoom_ligne *= param.zoom_ligne_out**(-wheel_ctrl_event_count)


    def EventOnMotion(self, event):
        self.motion_event = PseudoEvent(event)
        if event.LeftIsDown() and not self.HasCapture():
            self.CaptureMouse()

    def OnMotion(self, event):
        #if self.FindFocus() in (self.parent, self.parent.parent, self.parent.parent.parent):
        if self.GetTopLevelParent().IsEnabled() and (event.LeftIsDown() or event.RightIsDown()):
            self.SetFocus()
        if self.redetecter:
            self.detecter()
        actuelle = self.feuille_actuelle

        if actuelle.objet_temporaire(): # Utilis� pour la pr�visualisation d'objets, avant leur construction avec la souris
            actuelle.point_temporaire().coordonnees = self.coordonnees(event)

        if event.LeftIsDown():# or self.interaction:
            self.editeur.close()
            if event.ControlDown(): # selection d'un zone pour zoomer
                if event.AltDown(): # selection simultan�e de tous les objets d'une zone
                    self.selection_zone(event.GetPositionTuple())

                elif not self.fixe:
                    self.gestion_zoombox(event.GetPositionTuple())

            elif event.AltDown(): # deplacement de l'etiquette d'un objet
                self.debut_zoom = None
                x, y = event.GetPositionTuple()
                if self.etiquette_selectionnee is None:
                    for objet in actuelle.liste_objets(False):
                        if objet.etiquette is not None:
                            try:
                                if objet.etiquette.distance_inf(x, y, param.precision_selection):
                                    self.etiquette_selectionnee = objet.etiquette
                                    x, y = self.etiquette_selectionnee.coordonnees
                                    x1, y1 = self.coordonnees(event)
                                    self.decalage_coordonnees = x - x1, y - y1
                                    break
                            except:
                                print_error()
                                self.message(u"Erreur: impossible de trouver l'�tiquette de %s.." %objet.nom)
                if self.etiquette_selectionnee:
                    self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
                    self.etiquette_selectionnee(*self.coordonnees(event, *self.decalage_coordonnees))


            elif self.select is not None and not self.interaction: # deplacement d'un objet avec la souris
                self.debut_zoom = None
                if self.deplacable(self.select):
                    self.select(*self.coordonnees(event, *self.decalage_coordonnees))
                self.infos()

        elif event.RightIsDown() and self.debut_shift and not self.fixe: # deplacement de la feuille
            self.SetCursor(wx.StockCursor(wx.CURSOR_SIZING))
            self.fin_shift = self.pix2coo(*event.GetPositionTuple())
            translation = array(self.fin_shift) - array(self.debut_shift)
            self.fenetre = self.fenetre[0] - translation[0], self.fenetre[1] - translation[0], self.fenetre[2] - translation[1], self.fenetre[3] - translation[1]
            if self.select is not None:
                self.select = None
                self.selection_en_gras()

        elif self.interaction_deplacement is not None:
            self.interaction_deplacement(pixel = event.GetPositionTuple())

        elif not event.ControlDown():   # detection des objets a proximite du pointeur
            self.detecter(event.GetPositionTuple())



    def gestion_zoombox(self, pixel):
        x, y = pixel
        xmax, ymax = self.GetSize()
        x = max(min(x, xmax), 0)
        y = max(min(y, ymax), 0)
        self.fin_zoom = self.pix2coo(x, y)
        self.debut_zoom = self.debut_zoom or self.fin_zoom
        (x0, y0), (x1, y1) = self.debut_zoom, self.fin_zoom
        if self.orthonorme:
            if ymax*abs(x0 - x1) > xmax*abs(y0 - y1):
                y1 = y0 + ymax/xmax*abs(x0 - x1)*cmp(y1, y0)
            else:
                x1 = x0 + xmax/ymax*abs(y0 - y1)*cmp(x1, x0)
            self.fin_zoom = (x1, y1)
            #if param.bouger_curseur:  # ou comment rendre fou l'utilisateur... ;)
            #    self.WarpPointer(*self.XYcoo2pix((x1, y1), -1))
        self.dessiner_polygone([x0,x0,x1,x1], [y0,y1,y1,y0], facecolor='c', edgecolor='c', alpha = .1)
        self.dessiner_ligne([x0,x0,x1,x1,x0], [y0,y1,y1,y0,y0], 'c', alpha = 1)

        self.rafraichir_affichage(dessin_temporaire = True) # pour ne pas tout rafraichir


    def selection_zone(self, pixel):
        x, y = pixel
        xmax, ymax = self.GetSize()
        x = max(min(x, xmax), 0)
        y = max(min(y, ymax), 0)
        self.fin_select = self.pix2coo(x, y)
        self.debut_select = self.debut_select or self.fin_select
        (x0, y0), (x1, y1) = self.debut_select, self.fin_select
        self.dessiner_polygone([x0,x0,x1,x1], [y0,y1,y1,y0], facecolor='y', edgecolor='y',alpha = .1)
        self.dessiner_ligne([x0,x0,x1,x1,x0], [y0,y1,y1,y0,y0], 'g', linestyle = ":", alpha = 1)

        self.rafraichir_affichage(dessin_temporaire = True) # pour ne pas tout rafraichir







    def OnSelect(self, x0, x1, y0, y1):
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)
        objets_dans_la_zone = []
        for objet in self.feuille_actuelle.liste_objets():
            espace = objet.espace_vital
            if espace is not None:
                xmin, xmax, ymin, ymax = espace
                if x0 <= xmin <= xmax <= x1 and y0 <= ymin <= ymax <= y1:
                    objets_dans_la_zone.append(objet)
        self.feuille_actuelle.objets_en_gras(*objets_dans_la_zone)

        def exporte():
            actuelle = self.feuille_actuelle # feuille de travail courante
##            if actuelle.sauvegarde["export"]:
##                dir, fichier = os.path.split(actuelle.sauvegarde["export"]) # on exporte sous le m�me nom qu'avant par d�faut
##            elif actuelle.sauvegarde["nom"]:
##                fichier = actuelle.sauvegarde["nom"] # le nom par defaut est le nom de sauvegarde
##                dir = actuelle.sauvegarde["repertoire"]
##            else:
##                if param.rep_export is None:
##                    dir = param.repertoire
##                else:
##                    dir = param.rep_export

            filename = self.parent.parent.ExportFile(exporter = False)
            # ne pas faire l'export, mais r�cup�rer juste le nom

            if filename:
                self.exporter(nom = filename, zone = (x0, x1, y0, y1))
                actuelle.sauvegarde["export"] = filename

        if objets_dans_la_zone:
            dlg = wx.SingleChoiceDialog(self, u"Appliquer � la s�lection :", u"S�lection",
                        [u"Supprimer les objets", u"Masquer les objets", u"Editer les objets", u"Exporter la zone comme image"],
                        wx.CHOICEDLG_STYLE)

            if dlg.ShowModal() == wx.ID_OK:
                choix = dlg.GetSelection()
                if choix == 0:
                    with self.geler_affichage(actualiser = True):
                        for objet in objets_dans_la_zone:
                            self.executer(u"del %s" %objet.nom)
                elif choix == 1:
                    with self.geler_affichage(actualiser = True):
                        for objet in objets_dans_la_zone:
                            self.executer(u"%s.cacher()" %objet.nom)
                elif choix == 2:
                    win = Proprietes(self, objets_dans_la_zone)
                    win.Show(True)
                elif choix == 3:
                    exporte()

            dlg.Destroy()

            with self.geler_affichage():
                self.selection_en_gras()
        else:
            exporte()
        self.rafraichir_affichage()


    def OnLeftDown(self, event):
        # Patch pour l'utilisation avec un dispositif de pointage absolu (tablette graphique ou TNI)
        self.detecter(event.GetPositionTuple())
        if self.HasCapture():
            self.ReleaseMouse()
        self.SetFocus()
        if self.deplacable(self.select):
            x, y = self.select.coordonnees
            x1, y1 = self.coordonnees(event)
            self.decalage_coordonnees = x - x1, y - y1


    def OnLeftUp(self, event):
        if self.HasCapture():
            self.ReleaseMouse()

        if self.etiquette_selectionnee:
            x, y = self.etiquette_selectionnee.coordonnees
            self.parent.action_effectuee(u"%s.etiquette(%s, %s)" %(self.etiquette_selectionnee.parent.nom, x, y))
            self.etiquette_selectionnee = None
            return

        if self.debut_zoom and not self.fixe:
            #self.ReleaseMouse()
            try:
                if event.ControlDown():
                    (x0, y0), (x1, y1) = self.debut_zoom, self.fin_zoom
                    self.executer("fenetre = " + str((x0, x1, y0, y1)))
                else:
                    self.rafraichir_affichage()
            finally:
                self.debut_zoom = None

        elif self.debut_select and not self.fixe:
            #self.ReleaseMouse()
            try:
                if event.ControlDown() and event.AltDown():
                    (x0, y0), (x1, y1) = self.debut_select, self.fin_select
                    self.OnSelect(x0, x1, y0, y1)
                else:
                    self.rafraichir_affichage()
            finally:
                self.debut_select = None

        elif self.interaction:
            self.signal(event)
            self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))

        elif self.deplacable(self.select):
            self.parent.action_effectuee(self.select.nom + str(self.select.coordonnees))
            # pas super precis : il se peut qu'on relache le bouton sans avoir deplace le point.
            # ca fait un enregistrement inutile dans l'historique...



    def OnRightDown(self, event):
        self.editeur.close()
        self.detecter(event.GetPositionTuple())

        if self.select is not None and not event.ControlDown():
            menu = wx.Menu()
            # Contournement d'un bug de wxGtk
            if wx.Platform == '__WXGTK__':
                menu.Append(wx.NewId(), u" \u2714 " + self.select.nom_complet)
                menu.AppendSeparator()
            else:
                menu.SetTitle(self.select.nom_complet)
            selections = [obj for obj in self.selections if obj is not self.select] # autres objets a proximite
            n = len(selections)
            ids = [wx.NewId() for i in xrange(n + 7)]
            for i in range(n):
                def select(event, obj = selections[i]):
                    self.select = self.select_memoire = obj
                    self.selection_en_gras()
                menu.Append(ids[i], u"S�lectionner " + selections[i].nom_complet)
                menu.Bind(wx.EVT_MENU, select, id = ids[i])
            if n:
                menu.AppendSeparator()

            menu.Append(ids[n], u"Supprimer")
            def supprimer(event, select = self.select):
                self.executer(u"%s.supprimer()" %select.nom)
            menu.Bind(wx.EVT_MENU, supprimer, id = ids[n])

            if self.select.style("visible"):
                chaine = u"Masquer"
            else:
                chaine = u"Afficher"
            menu.Append(ids[n + 1], chaine)
            def masquer(event, select = self.select):
                self.executer(u"%s.style(visible = %s)" %(select.nom, not self.select.style("visible")))
            menu.Bind(wx.EVT_MENU, masquer, id = ids[n + 1])

            menu.Append(ids[n + 2], u"Renommer")
            def renommer(event, select = self.select):
                dlg = wx.TextEntryDialog(self, u"Note: pour personnaliser davantage le texte de l'objet,\nchoisissez \"Texte associ�\" dans le menu de l'objet.", u"Renommer l'objet", select.nom_corrige)
                test = True
                while test:
                    test = dlg.ShowModal()
                    if test == wx.ID_OK:
                        try:    # on renomme, et on met l'affichage de la l�gende en mode "Nom"
                            self.executer(u"%s.renommer(%s, legende = %s)" %(select.nom, repr(dlg.GetValue()), NOM))
                            break
                        except:
                            print_error()

                    if test == wx.ID_CANCEL:
                        break
                dlg.Destroy()
            menu.Bind(wx.EVT_MENU, renommer, id = ids[n + 2])

            msg = u"�diter le texte" if isinstance(self.select, Texte_generique) else u"Texte associ�"
            menu.Append(ids[n + 3], msg)
            def etiquette(event, select = self.select):
                old_style = select.style().copy()
                old_label = select.style(u"label")
                if old_label is None:   # le style label n'existe pas pour l'objet
                    return
                #dlg = wx.TextEntryDialog(self, "Note: le code LATEX doit etre entre $$. Ex: $\\alpha$", "Changer l'etiquette de l'objet", old_label, style = wx.TE_MULTILINE )
                #dlg.FitInside()
                dlg = wx.Dialog(self, -1, u"Changer la l�gende de l'objet (texte quelconque)")
                sizer = wx.BoxSizer(wx.VERTICAL)
                sizer.Add(wx.StaticText(dlg, -1, u"Note: le code LATEX doit etre entre $$. Ex: $\\alpha$"), 0, wx.ALIGN_LEFT|wx.ALL, 5)
                dlg.text = wx.TextCtrl(dlg, -1, old_label, size=wx.Size(300,50), style = wx.TE_MULTILINE)
                sizer.Add(dlg.text, 0, wx.ALIGN_LEFT|wx.ALL, 5)
                dlg.cb = wx.CheckBox(dlg, -1, u"Interpr�ter la formule")
                dlg.cb.SetValue(select.style(u"legende") == FORMULE)
                sizer.Add(dlg.cb, 0, wx.ALIGN_LEFT|wx.ALL, 5)
                line = wx.StaticLine(dlg, -1, size=(20,-1), style=wx.LI_HORIZONTAL)
                sizer.Add(line, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.TOP, 5)
                box = wx.BoxSizer(wx.HORIZONTAL)
                btn = wx.Button(dlg, wx.ID_OK)
                #btn.SetDefault()
                box.Add(btn, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
                btn = wx.Button(dlg, wx.ID_CANCEL, u" Annuler ")
                box.Add(btn, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
                sizer.Add(box, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
                dlg.SetSizer(sizer)
                sizer.Fit(dlg)
                dlg.CenterOnScreen()
                test = True
                while test:
                    test = dlg.ShowModal()
                    if test == wx.ID_OK:
                        try:
                            self.executer(u"%s.label(%s, %s)" %(select.nom, repr(dlg.text.GetValue()), dlg.cb.GetValue()))
                            break
                        except:
                            select.style(**old_style)
                            #~ print "Ancien style", old_style
                            print_error()
                    if test == wx.ID_CANCEL:
                        #select.label(old_label)
                        #~ select.style(**old_style)
                        break
                dlg.Destroy()
            menu.Bind(wx.EVT_MENU, etiquette, id = ids[n + 3])

            if self.select.label():
                chaine = u"Masquer"
            else:
                chaine = u"Afficher"
            menu.Append(ids[n + 4], chaine + u" nom/texte")
            def masquer_nom(event, select = self.select):
                if self.select.label():
                    mode = RIEN
                else:
                    if self.select.style(u"label"):
                        mode = TEXTE
                    else:
                        mode = NOM
                self.executer(u"%s.style(legende = %s)" %(select.nom, mode))
            menu.Bind(wx.EVT_MENU, masquer_nom, id = ids[n + 4])

            menu.AppendSeparator()

            menu.Append(ids[n + 5], u"Red�finir")
            def redefinir(event, select = self.select):
                nom = select.nom
                dlg = wx.TextEntryDialog(self, u"Exemple: transformez une droite en segment.", u"Red�finir l'objet", select._definition())
                test = True
                while test:
                    test = dlg.ShowModal()
                    if test == wx.ID_OK:
                        try:    # on red�finit l'objet
                            self.executer(u"%s.redefinir(%s)" %(nom, repr(dlg.GetValue())))
                            break
                        except:
                            print_error()

                    if test == wx.ID_CANCEL:
                        break
                dlg.Destroy()
            menu.Bind(wx.EVT_MENU, redefinir, id = ids[n + 5])

            menu.AppendSeparator()

            if isinstance(self.select, Point_generique):
                ids_relier = [wx.NewId(), wx.NewId(), wx.NewId()]
                relier = wx.Menu()
                relier.Append(ids_relier[0], u"aux axes")
                relier.Append(ids_relier[1], u"� l'axe des abscisses")
                relier.Append(ids_relier[2], u"� l'axe des ordonn�es")


                def relier0(event, self = self, select = self.select):
                    self.executer(u"%s.relier_axes()" %select.nom)
                relier.Bind(wx.EVT_MENU, relier0, id = ids_relier[0])

                def relier1(event, self = self, select = self.select):
                    self.executer(u"%s.relier_axe_x()" %select.nom)
                relier.Bind(wx.EVT_MENU, relier1, id = ids_relier[1])

                def relier2(event, self = self, select = self.select):
                    self.executer(u"%s.relier_axe_y()" %select.nom)
                relier.Bind(wx.EVT_MENU, relier2, id = ids_relier[2])

                menu.AppendMenu(wx.NewId(), u"Relier le point", relier)


                menu.AppendSeparator()

            menu.Append(ids[n + 6], u"Propri�t�s")
            def proprietes(event, select = self.select):
                win = Proprietes(self, [select])
                win.Show(True)
            menu.Bind(wx.EVT_MENU, proprietes, id = ids[n + 6])

            self.PopupMenu(menu)
            menu.Destroy()
            if self.select is not None:
                self.select = None
                self.selection_en_gras()
            self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))
        elif not self.fixe:
            self.debut_shift = self.pix2coo(*event.GetPositionTuple())
            self.SetCursor(wx.StockCursor(wx.CURSOR_SIZING))
            if not self.HasCapture():
                self.CaptureMouse()




    def OnRightUp(self, event):
        if self.HasCapture():
            self.ReleaseMouse()

        if self.fixe: return

        self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))

        if self.debut_shift:
            self.debut_shift= None
            self.parent.action_effectuee(u"fenetre = " + str(self.fenetre))


    def editer(self, mode = 0):
        if self.select is not None:
            self.editeur.init(self.select, mode)
        else:
            self.editeur.close()


    def OnChar(self, event):
        if self.redetecter:
            self.detecter()

        key = event.GetKeyCode()
        debug(u"key: ", key)
        if key == wx.WXK_DELETE and self.select:
            if event.ShiftDown():
                self.executer(u"%s.cacher()" %self.select.nom)
            else:
                self.executer(u"%s.supprimer()" %self.select.nom)
        if (key == wx.WXK_RETURN or key == wx.WXK_NUMPAD_ENTER) and self.editeur.objet is not self.select:
            self.editer(event.ShiftDown())
        elif self.editeur:
            self.editeur.key(key)

        if key == wx.WXK_ESCAPE and self.interaction:
            print "ESCAPE !"
            self.interaction(special = "ESC")

        if key < 256:debug(unichr(key))
        event.Skip()



    def OnPaint(self, event):
        self.graph.restaurer_dessin()
        if param.plateforme == "Windows":
            event.Skip()


    def OnSize(self, event):
        self.feuille_actuelle._rafraichir_figures()
        self.rafraichir_affichage(rafraichir_axes = True)
        event.Skip()

    def OnLeave(self, event):
        self.execute_on_idle(self.feuille_actuelle.objets_en_gras)
