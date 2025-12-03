# OnCutF Companion Files - Edge Cases & Mixed File Types

## Πώς Χειρίζεται το Σύστημα Διαφορετικούς Τύπους Αρχείων

### 1. **XML Αρχεία στον Ίδιο Φάκελο**

#### Sony Camera XML (Ανιχνεύονται ως Companions)
```
movie.MP4
movieM01.XML  ← Ανιχνεύεται ως Sony companion
movieM02.XML  ← Ανιχνεύεται ως Sony companion (backup metadata)
```

**Κριτήρια Ανίχνευσης:**
- Pattern matching: `movie` + `M01.XML` ή `M02.XML`
- Root element validation: `<NonRealTimeMeta>`

#### Άλλα XML Αρχεία (Αγνοούνται)
```
movie.MP4
config.xml      ← Αγνοείται (δεν ακολουθεί Sony pattern)
settings.xml    ← Αγνοείται 
movie_backup.xml ← Αγνοείται (δεν είναι movieM01.XML)
project.xml     ← Αγνοείται
```

### 2. **Subtitle Αρχεία (Ανιχνεύονται ως Companions)**

#### Υποστηριζόμενοι Τύποι
```
movie.MP4
movie.srt   ← Ανιχνεύεται ως companion
movie.vtt   ← Ανιχνεύεται ως companion  
movie.ass   ← Ανιχνεύεται ως companion
```

#### Χειρισμός Subtitles
- **Detection**: Pattern matching με βάση το filename
- **Metadata**: Δεν εξάγεται metadata από SRT (expected behavior)
- **Rename Sync**: Αυτόματη μετονομασία μαζί με το MP4
- **Table Visibility**: Κρύβονται από τον πίνακα (configurable)

### 3. **Μικτοί Φάκελοι - Παράδειγμα**

```
📁 Wedding_Footage/
├── ceremony.MP4           ← Main video file
├── ceremonyM01.XML        ← Sony metadata (detected)
├── ceremony.srt           ← English subtitles (detected)
├── ceremony_gr.srt        ← Greek subtitles (NOT detected - different name)
├── project_config.xml     ← Project file (ignored)
├── backup.xml             ← Backup file (ignored)
├── ceremony.vtt           ← Web subtitles (detected)
└── README.txt             ← Documentation (ignored)
```

**Αποτέλεσμα:**
- Στον πίνακα φαίνεται μόνο: `ceremony.MP4`
- Companions: `ceremonyM01.XML`, `ceremony.srt`, `ceremony.vtt`
- Αγνοούνται: `ceremony_gr.srt`, `project_config.xml`, `backup.xml`, `README.txt`

### 4. **Smart Detection Logic**

#### Pattern Matching
```python
# Sony XML patterns (case-insensitive)
r"^(.+)M01\.XML$"  # movie.MP4 → movieM01.XML
r"^(.+)M02\.XML$"  # movie.MP4 → movieM02.XML

# Subtitle patterns
r"^(.+)\.srt$"     # movie.MP4 → movie.srt
r"^(.+)\.vtt$"     # movie.MP4 → movie.vtt
r"^(.+)\.ass$"     # movie.MP4 → movie.ass
```

#### Content Validation
- **Sony XML**: Ελέγχει για `<NonRealTimeMeta>` root element
- **Other XML**: Αγνοείται αν δεν είναι Sony format
- **Subtitles**: Δεν γίνεται content validation

### 5. **Metadata Integration**

#### Sony XML Enhanced Metadata
```
Base MP4 metadata:
├── FileName: ceremony.MP4
├── FileSize: 2.1 GB
└── FileType: MP4

Enhanced με Sony XML:
├── FileName: ceremony.MP4
├── FileSize: 2.1 GB  
├── FileType: MP4
├── Companion:ceremonyM01.XML:device_manufacturer: Sony
├── Companion:ceremonyM01.XML:device_model: FX6
├── Companion:ceremonyM01.XML:video_codec: XAVC S
├── Companion:ceremonyM01.XML:video_resolution: 3840x2160
└── __companion_files__: [ceremonyM01.XML, ceremony.srt, ceremony.vtt]
```

#### Non-Companion Files
- **Ignored XML**: Δεν επηρεάζει το metadata
- **Subtitle Files**: Περιλαμβάνονται στο `__companion_files__` αλλά δεν προσθέτουν metadata

### 6. **User Experience**

#### Διαφανής Λειτουργία
- Μόνο τα main files εμφανίζονται στον πίνακα
- Companions αυτόματα συνδέονται και διαχειρίζονται
- Non-companion files εμφανίζονται κανονικά

#### Batch Operations
```
Επιλογή: ceremony.MP4, reception.MP4
Rename operation επηρεάζει:
├── ceremony.MP4 → Wedding_Ceremony.MP4
├── ceremonyM01.XML → Wedding_CeremonyM01.XML  
├── ceremony.srt → Wedding_Ceremony.srt
├── reception.MP4 → Wedding_Reception.MP4
└── receptionM01.XML → Wedding_ReceptionM01.XML

Δεν επηρεάζονται:
├── project_config.xml (remains unchanged)
└── backup.xml (remains unchanged)
```

### 7. **Configuration Options**

#### Companion File Behavior
```python
COMPANION_FILES_ENABLED = True        # Master switch
SHOW_COMPANION_FILES_IN_TABLE = False # Hide from table
AUTO_RENAME_COMPANION_FILES = True    # Sync rename operations  
LOAD_COMPANION_METADATA = True        # Include in metadata
```

#### Fine-Grained Control
- Users μπορούν να δουν companions στον πίνακα αν θέλουν
- Rename sync μπορεί να απενεργοποιηθεί
- Metadata loading μπορεί να γίνει selective

### 8. **Best Practices**

#### Φάκελος Organization
```
✅ Καλή δομή:
├── video001.MP4 + video001M01.XML + video001.srt
├── video002.MP4 + video002M01.XML + video002.srt  
└── video003.MP4 + video003M01.XML + video003.srt

⚠️ Προβληματική δομή:
├── video001.MP4 + video001M01.XML
├── video001_backup.srt (δεν θα ανιχνευθεί)
├── project.xml (θα αγνοηθεί αλλά δημιουργεί σύγχυση)
└── video001_greek.srt (δεν θα ανιχνευθεί)
```

#### Professional Workflows
- Χρησιμοποιήστε consistent naming από την κάμερα
- Τοποθετήστε project files σε ξεχωριστό φάκελο
- Κρατήστε subtitles με ίδιο όνομα με το video

Το OnCutF σύστημα είναι σχεδιασμένο να χειρίζεται έξυπνα μικτούς φακέλους, αναγνωρίζοντας μόνο τα πραγματικά companion files και αγνοώντας άσχετα αρχεία.