# -*- coding: iso-8859-1 -*-
from __future__ import division # 1/2 == .5 (par defaut, 1/2 == 0)


calcul_exact = True    # gerer les fractions et les racines de maniere exacte si possible.
ecriture_scientifique = False # afficher les resultats en ecriture scientifique.
changer_separateurs = False # appliquer les separateurs personnalises
separateurs_personnels = (",", ";") # separateurs personnalises (separateur decimal, separateur de listes)
# d'autres choix sont possibles, mais pas forcement heureux...
copie_automatique = False # copie automatique de chaque resultat dans le presse-papier
copie_automatique_LaTeX = False
formatage_OOo = True
formatage_LaTeX = True
ecriture_scientifique_decimales = 2
precision_calcul = 60
precision_affichage = 18
forme_affichage_complexe = ("algebrique", "exponentielle")[0]
# Fonction � appliquer � tout r�sultat avant de le renvoyer :
appliquer_au_resultat = None
