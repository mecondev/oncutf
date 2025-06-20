# Preferences System Documentation

## Περιγραφή

Το preferences system του oncutf είναι ένα ολοκληρωμένο σύστημα διαχείρισης ρυθμίσεων που χρησιμοποιεί JSON αρχεία για την αποθήκευση και φόρτωση των προτιμήσεων του χρήστη.

## Χαρακτηριστικά

- **Πολλαπλές κατηγορίες ρυθμίσεων**: Window, File Hashes, App preferences
- **Αυτόματη δημιουργία backup**: Δημιουργεί αντίγραφα ασφαλείας πριν την αποθήκευση
- **Thread-safe operations**: Ασφαλής χρήση σε πολυνηματικό περιβάλλον
- **Default values**: Προεπιλεγμένες τιμές για όλες τις ρυθμίσεις
- **Cross-platform**: Λειτουργεί σε Windows και Linux

## Δομή Αρχείου

Το preferences αρχείο αποθηκεύεται στο:
- **Linux**: `~/.config/oncutf/preferences.json`
- **Windows**: `%APPDATA%/oncutf/preferences.json`

## Κατηγορίες Ρυθμίσεων

### 1. Window Preferences
```json
{
  "window": {
    "geometry": {"x": 100, "y": 100, "width": 1200, "height": 900},
    "window_state": "normal",
    "splitter_states": {
      "horizontal": [250, 674, 250],
      "vertical": [500, 300]
    },
    "column_widths": {
      "file_table": [23, 345, 80, 60, 130],
      "metadata_tree": [180, 500]
    },
    "last_folder": "",
    "recursive_mode": false,
    "sort_column": 1,
    "sort_order": 0
  }
}
```

### 2. File Hash Preferences
```json
{
  "file_hashes": {
    "enabled": true,
    "algorithm": "sha256",
    "cache_size_limit": 10000,
    "auto_cleanup_days": 30,
    "hashes": {
      "/path/to/file.jpg": {
        "hash": "abc123def456",
        "timestamp": "2025-06-20T21:26:56.733254",
        "size": 1024000
      }
    }
  }
}
```

### 3. App Preferences
```json
{
  "app": {
    "theme": "dark",
    "language": "en",
    "auto_save_preferences": true,
    "recent_folders": ["/path/to/recent/folder"]
  }
}
```

## Χρήση

### Βασική Χρήση
```python
from utils.preferences_manager import get_preferences_manager

# Λήψη του preferences manager
prefs = get_preferences_manager()

# Ανάγνωση τιμής
window_width = prefs.window.get('geometry')['width']

# Αποθήκευση τιμής
prefs.window.set('window_state', 'maximized')

# Αποθήκευση σε αρχείο
prefs.save()
```

### Διαχείριση File Hashes
```python
# Προσθήκη hash αρχείου
prefs.file_hashes.add_file_hash('/path/to/file.jpg', 'sha256_hash', 1024000)

# Λήψη hash αρχείου
hash_info = prefs.file_hashes.get_file_hash('/path/to/file.jpg')
if hash_info:
    print(f"Hash: {hash_info['hash']}")
    print(f"Size: {hash_info['size']}")
```

### Διαχείριση Recent Folders
```python
# Προσθήκη πρόσφατου φακέλου
prefs.app.add_recent_folder('/path/to/folder')

# Λήψη πρόσφατων φακέλων
recent = prefs.app.get('recent_folders', [])
```

## Ενσωμάτωση στο MainWindow

Το preferences system είναι πλήρως ενσωματωμένο στο MainWindow:

### Κατά την Εκκίνηση
1. Φορτώνει τις ρυθμίσεις από το JSON αρχείο
2. Εφαρμόζει τη γεωμετρία του παραθύρου
3. Αποκαθιστά τις καταστάσεις των splitters
4. Επαναφέρει τα μεγέθη των στηλών

### Κατά το Κλείσιμο
1. Αποθηκεύει την τρέχουσα γεωμετρία του παραθύρου
2. Αποθηκεύει τις καταστάσεις των splitters
3. Αποθηκεύει τα μεγέθη των στηλών
4. Αποθηκεύει τον τελευταίο φάκελο και τις ρυθμίσεις

## Μεθόδοι MainWindow

### `_load_window_preferences()`
Φορτώνει και εφαρμόζει τις ρυθμίσεις του παραθύρου κατά την εκκίνηση.

### `_save_window_preferences()`
Αποθηκεύει την τρέχουσα κατάσταση του παραθύρου κατά το κλείσιμο.

### `_apply_loaded_preferences()`
Εφαρμόζει τις ρυθμίσεις UI μετά την αρχικοποίηση του interface.

### `restore_last_folder_if_available()`
Επαναφέρει τον τελευταίο φάκελο αν υπάρχει και είναι διαθέσιμος.

## Αρχεία Backup

Το σύστημα δημιουργεί αυτόματα backup αρχεία:
- `preferences.backup.json` - Αντίγραφο ασφαλείας
- Αυτόματη επαναφορά σε περίπτωση σφάλματος

## Thread Safety

Το preferences system είναι thread-safe με χρήση `threading.RLock()` για την προστασία των δεδομένων.

## Επέκταση

Για να προσθέσετε νέες κατηγορίες preferences:

1. Δημιουργήστε νέα κλάση που κληρονομεί από `PreferenceCategory`
2. Προσθέστε την στον `PreferencesManager.__init__()`
3. Ενημερώστε τις μεθόδους `load()` και `save()`

## Παραδείγματα Χρήσης

### Test Script
Δείτε το `test_preferences.py` για παραδείγματα χρήσης όλων των χαρακτηριστικών.

### Debugging
```python
# Εμφάνιση πληροφοριών preferences
info = prefs.get_preferences_info()
print(info)

# Εμφάνιση περιεχομένου αρχείου
import json
with open(prefs.preferences_file, 'r') as f:
    content = json.load(f)
print(json.dumps(content, indent=2))
```

## Troubleshooting

### Σφάλματα Φόρτωσης
- Ελέγχει αν το αρχείο είναι έγκυρο JSON
- Αυτόματη επαναφορά από backup
- Χρήση προεπιλεγμένων τιμών σε περίπτωση σφάλματος

### Σφάλματα Αποθήκευσης
- Δημιουργία backup πριν την αποθήκευση
- Χρήση temporary αρχείου για atomic operations
- Λεπτομερή logs για debugging
