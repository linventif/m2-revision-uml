# Diagrammes UML des design patterns

Un diagramme de classes par pattern (les 23 du GoF + MVC en bonus + l'exercice de révision ON/OFF), avec les mêmes classes que dans [../design-patterns-cheatsheet.md](../design-patterns-cheatsheet.md).

| Dossier | Format | À ouvrir avec |
|---|---|---|
| `plantuml/` | PlantUML (`.puml`) | VS Code + extension **PlantUML** (jebbs.plantuml) |
| `xmi/` | XMI 2.1 / UML 2.1 (`.xmi`) | Visual Paradigm, StarUML, Enterprise Architect… |

## VS Code (PlantUML)

1. Installer l'extension **PlantUML** (`jebbs.plantuml`). Java doit être installé.
2. Ouvrir un `.puml`, puis `Alt+D` pour l'aperçu.
3. Export PNG/SVG : palette de commandes → *PlantUML: Export Current Diagram*.

Les fichiers contiennent `!pragma layout smetana` : Graphviz n'est donc **pas** nécessaire.
Chaque diagramme a une légende en bas avec le **But** et la **Lecture** du pattern.
Diagrammes en plus :
- `16-state-transitions.puml` : l'automate des états de State ;
- `24-mvc-sequence.puml` : diagramme de séquence du cycle MVC (clic → contrôleur → modèle → vues).

**Exercice de révision ON/OFF** (fichiers 25 et 26) :
- `25-on-off-mvc-observer-command.puml` : diagramme de classes MVC + Observer + Command ;
- `25-on-off-mvc-observer-command-transitions.puml` : diagramme d'états Éteint / Allumé ;
- `25-on-off-mvc-observer-command-sequence.puml` : ce qui se passe quand on clique sur ON ;
- `26-on-off-version-state.puml` : le même modèle avec le pattern State (+ Singleton).

## Visual Paradigm (XMI)

1. *File > Import > XMI…* et choisir un fichier du dossier `xmi/`.
   `00-tous-les-patterns.xmi` importe tous les diagrammes d'un coup, chacun dans son package.
2. Les classes, attributs, méthodes et relations arrivent dans le *Model Explorer*.
3. Pour avoir le dessin : créer un *Class Diagram*, y glisser les classes du package,
   puis *Diagram > Layout Diagram* pour les ranger.

Le XMI contient le **modèle** (classes et relations), pas la position des boîtes :
c'est pour ça qu'il faut glisser les classes sur un diagramme après l'import.

## Regénérer

Les fichiers sont produits à partir des diagrammes Mermaid de la cheatsheet.
Après avoir modifié la cheatsheet : `python3 design-patterns-uml/generer.py`.
