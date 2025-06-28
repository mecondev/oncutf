# Database System Quick Start

## Overview

Το oncutf περιλαμβάνει τώρα ένα ολοκληρωμένο σύστημα βάσης δεδομένων που παρέχει:

- **Persistent Metadata Storage**: Αποθήκευση metadata που διατηρείται μεταξύ των sessions
- **Hash Caching**: Persistent caching των CRC32 hashes για καλύτερη απόδοση
- **Rename History**: Undo/redo functionality για rename operations
- **Enhanced Performance**: Memory caching με database fallback

## Βασικά Χαρακτηριστικά

### 🗄️ Persistent Storage
- Όλα τα metadata και hashes αποθηκεύονται μόνιμα
- Γρήγορη πρόσβαση με memory caching
- Αυτόματη συντήρηση και καθαρισμός

### ↩️ Undo Functionality
- Πλήρης καταγραφή rename operations
- Undo με validation και integrity checking
- Batch operations support

### ⚡ Performance
- Thread-safe operations
- Connection pooling
- Optimized database queries
- Lazy loading με smart caching

## Χρήση

### Αυτόματη Ενεργοποίηση
Το database system ενεργοποιείται αυτόματα όταν ξεκινάει η εφαρμογή. Δεν χρειάζεται καμία ρύθμιση.

### Τοποθεσία Database
- **Linux**: `~/.local/share/oncutf/oncutf_data.db`
- **Windows**: `%APPDATA%/oncutf/oncutf_data.db`

### Νέες Λειτουργίες

#### Rename History
- Πατήστε `Ctrl+Z` για undo της τελευταίας rename operation
- Δείτε όλο το history μέσω του Tools menu
- Validation για safe undo operations

#### Database Statistics
- Δείτε στατιστικά χρήσης της βάσης δεδομένων
- Monitor cache performance
- Cleanup tools για παλιά δεδομένα

## Testing

Για να δοκιμάσετε το νέο σύστημα:

```bash
python scripts/test_database_system.py
```

Αυτό το script:
- Δημιουργεί test data
- Δοκιμάζει όλες τις λειτουργίες
- Επαληθεύει την ορθή λειτουργία
- Καθαρίζει τα temporary files

## Backward Compatibility

Το νέο σύστημα είναι πλήρως backward compatible:
- Ο υπάρχων κώδικας συνεχίζει να λειτουργεί
- Τα παλιά APIs διατηρούνται
- Αυτόματη migration από memory-only caches
- Graceful fallback σε περίπτωση προβλημάτων

## Troubleshooting

### Συνηθισμένα Προβλήματα

1. **Database Locked**: Συνήθως λύνεται αυτόματα
2. **Permission Errors**: Ελέγξτε δικαιώματα στον data directory
3. **Performance Issues**: Χρησιμοποιήστε cleanup tools

### Debug Mode
```python
import logging
logging.getLogger('core.database_manager').setLevel(logging.DEBUG)
```

### Manual Reset
Αν υπάρχουν προβλήματα:
1. Κλείστε την εφαρμογή
2. Διαγράψτε το database file
3. Επανεκκινήστε (θα δημιουργηθεί νέα βάση)

## Περισσότερες Πληροφορίες

- **Πλήρης Documentation**: [`docs/database_system.md`](database_system.md)
- **Test Suite**: [`tests/test_database_system.py`](../tests/test_database_system.py)
- **Demo Script**: [`scripts/test_database_system.py`](../scripts/test_database_system.py)

## Μελλοντικές Βελτιώσεις

- Compression για μεγάλα metadata
- Optional encryption
- Backup/restore functionality
- Cloud synchronization
- Export/import capabilities

---

Το νέο database system παρέχει solid foundation για μελλοντικές επεκτάσεις και βελτιώσεις της εφαρμογής!
