# OnCutF Companion Files - Quick User Guide

## Τι είναι τα Companion Files;

Τα companion files είναι επιπλέον αρχεία που δημιουργούν οι κάμερες και άλλες συσκευές μαζί με τα κύρια αρχεία:

- **Sony Cameras**: `C8227.MP4` + `C8227M01.XML` (metadata)
- **RAW Photos**: `IMG_1234.CR2` + `IMG_1234.xmp` (sidecar)
- **Video Subtitles**: `movie.mp4` + `movie.srt` (υπότιτλοι)

## Πώς Λειτουργεί στο OnCutF

### Αυτόματη Ανίχνευση
Όταν ανοίγετε φάκελο με Sony camera files:
- Εμφανίζονται μόνο τα MP4 αρχεία (210 files αντί για 420)
- Τα XML companions αυτόματα συνδέονται με τα MP4

### Enhanced Metadata Loading
Όταν φορτώνετε metadata (Ctrl+M):
```
Κανονικό MP4 metadata:
├── FileName: C8227.MP4
├── FileSize: 1.2 GB
└── FileType: MP4

Enhanced με Sony XML:
├── FileName: C8227.MP4  
├── FileSize: 1.2 GB
├── FileType: MP4
├── Companion:C8227M01.XML:device_manufacturer: Sony
├── Companion:C8227M01.XML:device_model: FX30
├── Companion:C8227M01.XML:video_codec: XAVC S
├── Companion:C8227M01.XML:video_resolution: 3840x2160
└── Companion:C8227M01.XML:audio_codec: PCM
```

### Automatic Rename Sync
Όταν μετονομάζετε αρχεία:
- `C8227.MP4` → `Wedding_Ceremony.MP4`
- `C8227M01.XML` → `Wedding_Ceremony_M01.XML` (αυτόματα!)

## Ρυθμίσεις

Μπορείτε να ελέγξετε τη συμπεριφορά από τις ρυθμίσεις:

- **Show companion files**: Εμφάνιση companions στον πίνακα
- **Auto-rename companions**: Αυτόματη μετονομασία companions
- **Load companion metadata**: Ενσωμάτωση companion metadata

## Υποστηριζόμενοι Τύποι

✅ **Sony Cameras**: XML metadata files  
✅ **RAW Photos**: XMP sidecar files  
✅ **Video Subtitles**: SRT, VTT, ASS files  
🔄 **Coming Soon**: Canon, Panasonic, BlackMagic

## Οφέλη

- **Καθαρότερος Workspace**: Μόνο τα κύρια αρχεία στη λίστα
- **Πλουσιότερα Metadata**: Camera info αυτόματα διαθέσιμα
- **Professional Workflow**: Συγχρονισμένες λειτουργίες
- **Αυτόματη Διαχείριση**: Δεν χρειάζεται manual handling

## Tips

1. **Batch Operations**: Επιλέξτε πολλά MP4 - τα XML θα ακολουθήσουν
2. **Metadata Export**: Τα companion metadata περιλαμβάνονται στο export
3. **Search/Filter**: Χρησιμοποιήστε companion metadata για filtering
4. **Backup**: Τα companions συμπεριλαμβάνονται στα backups

Το OnCutF αναγνωρίζει και διαχειρίζεται αυτόματα τα companion files χωρίς να χρειάζεται επέμβαση από εσάς!