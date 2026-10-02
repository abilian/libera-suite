# Utiliser Libera Suite

Libera Suite ouvre un document dans une fenêtre et vous permet de le modifier et de l'enregistrer. Words, Tables et Slides fonctionnent tous ainsi ; Diagrams ouvre les documents Visio en lecture.

Commencez par [Installer](../main/install.md). Ces trois pages se lisent dans l'ordre :

1. [Installer](../main/install.md) : l'installer sur votre machine, en une commande.
2. [Travailler sur des documents](documents.md) : ouvrir, enregistrer, exporter, imprimer.
3. [État des lieux](../main/status.md) : les fonctions disponibles et les problèmes que nous connaissons déjà.

Chaque éditeur a sa propre couleur. Pour le reste, la fenêtre est la même :

![Libera Tables contient une feuille de calcul vide, et sa barre d'outils est dans le bleu-vert de Libera Tables.](../assets/tables.png)

![Libera Slides contient une diapositive de titre, et sa barre d'outils est dans l'or de Libera Slides.](../assets/slides.png)

## Comment c'est fait

Libera Suite se compose de deux parties qui arrivent séparément.

**L'application** est un petit paquet Python. Elle pèse quelques centaines de kilo-octets : la fenêtre, la ligne de commande et l'application hôte avec laquelle l'éditeur communique.

**Les éditeurs** sont tout le reste : le moteur de documents, les éditeurs eux-mêmes, les polices. L'application appelle cet ensemble le *payload*. Il pèse environ 110 Mo compressé sous macOS et 120 Mo sous Linux. Vous le téléchargez ou l'installez une fois ; le paquet Python ne l'inclut pas.

Les deux ont des numéros de version distincts. L'application vérifie que les éditeurs qu'elle trouve sont bien ceux qu'elle attend. Une correction de l'application n'oblige donc pas à retélécharger les éditeurs.

L'installateur Windows et le Flatpak Linux contiennent les deux parties. Toutes les autres façons d'installer mettent d'abord l'application en place, puis téléchargent les éditeurs une fois.

## Ses limites

Libera Suite ne parle à aucun serveur, ne demande aucun compte et n'envoie jamais vos documents nulle part. L'éditeur s'exécute comme un contenu web local, servi sur `127.0.0.1` à une fenêtre de votre propre machine. Il n'y a ni collaboration, ni stockage en ligne, ni télémétrie, parce que rien de tout cela n'est construit.
