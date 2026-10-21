# 🎮 Intersect GUI Editor v1.0

Éditeur visuel pour les fichiers JSON d'interface d'**Intersect Engine**.

## ✨ Fonctionnalités

- **📂 Explorateur de fichiers** — Parcourez votre dossier GUI et ouvrez les fichiers JSON en double-clic
- **🖼️ Prévisualisation fidèle** — Canvas aux coordonnées réelles du jeu (800x600, 1024x768, 1280x720, 1920x1080)
- **🖱️ Drag & Drop** — Déplacez et redimensionnez les éléments directement sur le canvas
- **🌳 Arbre d'éléments** — Hiérarchie complète des éléments avec visibilité
- **⚙️ Éditeur de propriétés** — Modifiez Bounds, Texture, Hidden, couleurs, etc.
- **🔍 Zoom & Grille** — Molette pour zoomer, clic droit pour panoramique, snap to grid
- **💾 Sauvegarde** — Sauvegardez directement dans les fichiers JSON originaux
- **↩ Undo/Redo** — Ctrl+Z / Ctrl+Y
- **🎨 Textures** — Affichage des textures si le dossier est détecté
- **➕ Ajouter/Dupliquer/Supprimer** des éléments

## 🚀 Installation rapide (Windows)

### Méthode 1 : Lancer directement avec Python
1. Installez [Python 3.10+](https://www.python.org/downloads/) (cochez "Add to PATH")
2. Ouvrez un terminal dans le dossier du projet
3. Lancez :
   ```
   pip install Pillow
   python intersect_gui_editor.py
   ```

### Méthode 2 : Compiler en .exe
1. Installez [Python 3.10+](https://www.python.org/downloads/) (cochez "Add to PATH")
2. Double-cliquez sur `build.bat`
3. L'exécutable sera dans `dist/IntersectGUIEditor.exe`

## 🎮 Comment utiliser

1. **Ouvrir un dossier** : Cliquez `📂 Dossier` et sélectionnez le dossier `gui` de votre client Intersect
   - Chemin typique: `Intersect Client/resources/gui/`
2. **Ouvrir un fichier** : Double-cliquez sur un fichier JSON dans l'explorateur
3. **Éditer** : Cliquez sur un élément dans le canvas ou l'arbre pour le sélectionner
4. **Déplacer** : Glissez l'élément sur le canvas (positions = coordonnées in-game réelles)
5. **Redimensionner** : Attrapez les poignées bleues autour de l'élément
6. **Modifier les propriétés** : Utilisez le panneau de droite
7. **Sauvegarder** : Ctrl+S ou `💾 Sauver`

## ⌨️ Raccourcis

| Raccourci | Action |
|-----------|--------|
| Ctrl+O | Ouvrir dossier |
| Ctrl+F | Ouvrir fichier |
| Ctrl+S | Sauvegarder |
| Ctrl+Z | Annuler |
| Ctrl+Y | Rétablir |
| Ctrl+D | Dupliquer |
| Delete | Supprimer |
| Molette | Zoom |
| Clic droit + glisser | Panoramique |

## 📁 Structure des fichiers GUI Intersect

Les fichiers JSON se trouvent généralement dans :
```
Intersect Client/
└── resources/
    └── gui/
        ├── game/
        │   ├── ChatboxWindow.json
        │   ├── CharacterWindow.json
        │   ├── InventoryWindow.json
        │   └── ...
        └── menu/
            ├── LoginWindow.json
            ├── MainMenuWindow.json
            └── ...
```
