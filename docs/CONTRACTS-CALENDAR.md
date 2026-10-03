# Vertragsmanagement und Kalender — 0.6.0

## Datierte Vertragsstände

Ein Einnahmen-/Ausgaben-Eintrag hat zwei Zeitreihen: Preisänderungen und
Vertragsstände. Ein Vertragsstand speichert Name, Anbieter, Zahlungsintervall,
Währung, Laufzeit, Kündigung, Verlängerung, Konto, Rubrik, Vertragsinhaber und
Benutzerzuordnung sowie übrige Eintragsfelder. Historische Namen/Farben bleiben
im Stand gespeichert, auch wenn ein Katalogeintrag später umbenannt wird.

Für jedes Datum gilt der letzte Stand mit Wirksamkeitsdatum bis zu diesem Tag.
Änderungen mit zukünftigem Datum werden als geplant angezeigt und beeinflussen
aktuelle Listen, Erinnerungen und KI-Auswahl erst ab diesem Datum. Ein neuer
Stand ersetzt einen vorhandenen Stand am selben Tag; spätere geplante Stände
werden nicht automatisch umgeschrieben. Prüfe diese bei weiteren Änderungen.

Der Assistent bietet getrennte Daten für Preis und Vertragsangaben. Wird nur
Metadaten geändert, bleibt die bestehende Preisplanung erhalten. Rückwirkende
Änderungen sind bewusste Korrekturen ab dem gewählten Datum. Frühere Zeiträume
werden nicht überschrieben. Kalenderdetails erlauben das Bearbeiten einzelner
Stände und das getrennte Entfernen zukünftiger Stände oder zukünftiger Preise.

## Laufzeit, Kündigung und Verlängerung

Eine Kündigungsfrist in Tagen berechnet das Kündigungsdatum aus dem Vertragsende.
Ein festes Datum ist unabhängig davon. Automatische Verlängerung benötigt
Vertragsende und Verlängerungsmonate. Verlängerungen werden immer vom
ursprünglichen Vertragsende aus berechnet, sodass z. B. der 31. Januar nach einem
kurzen Februar wieder zum 31. März verlängert werden kann.

Der Verlängerungspreis gilt je Zahlungsintervall ab dem Tag nach dem ursprünglichen
Ende. Ein expliziter Preisstand nach diesem Ende hat Vorrang. Eine Kündigung oder
ein abgeschaltetes Auto-Renew beendet die weitere Verlängerung. Status
„gekündigt“ lässt Kosten bis zum Vertragsende bestehen; „beendet“ oder „pausiert“
stoppen die Kosten ab dem Datum des jeweiligen Vertragsstandes.

## Kalender und Kosten

Die Jahresansicht zeigt Verträge als Zeilen mit Zeitbalken. Monat und Woche teilen
die Achse in Tage; die Tagesansicht zeigt ganztägige Vertragskosten. Verträge
haben Tagesgenauigkeit, keine erfundenen Uhrzeiten. Wirksamkeits- und Preisgrenzen
teilen die Balken. Die Balken sind auf den angezeigten Zeitraum begrenzt; die
Details nennen zusätzlich den Vertragsbeginn und das vertragliche Ende.

Für wiederkehrende Kosten gilt:

```
Tageskosten = Betrag je Zahlungsintervall / Intervallmonate / Tage im Monat
Zeitraumskosten = Summe der Tageskosten im gültigen Zeitraum
```

Ein Preiswechsel mitten im Monat teilt die Monatskosten entsprechend. Einmalige
Einträge erzeugen genau am Buchungsdatum den vollen Betrag. Es werden keine
Kosten vor dem ersten bekannten Datum, während Pausen, nach einem beendeten
Vertrag oder jenseits einer Archivierungsgrenze erzeugt. Summen werden nach
Währung getrennt und erst nach dem Zusammenzählen gerundet; einzelne Balken zeigen
gerundete Teilbeträge. Währungen werden nicht automatisch umgerechnet.

Die Kalenderfilter beeinflussen Balken und Summen. Unbefristete Einträge,
Altlasten/frühere Stände und einzelne Einträge sind ausblendbar. Individuelle
Sichtbarkeit wird lokal je Benutzer gespeichert, nicht auf andere Geräte
übertragen. Die aufklappbare Eintragsverwaltung listet auch Einträge ohne Balken
im aktuellen Zeitraum. So bleiben Altbestände und Archive immer erreichbar.

Historische Dashboard-Summen und Rubrikverteilungen berücksichtigen die datierten
Vertragsstände und Kostenanteile. Das bisherige Dashboard verwendet weiterhin
EUR; Fremdwährungen sollten dort zuvor manuell umgerechnet werden.

## Archivierung und Datenschutz

„Im Kalender behalten“ entfernt den Eintrag aus der laufenden Liste und lässt
seine Kosten einschließlich des Archivierungstages bestehen. Zukünftige Kosten
werden nicht geplant. Eine Wiederherstellung behält die Archivierungslücke und
führt den dann gültigen Vertragsstand wieder fort; ein ausgelaufener Vertrag
benötigt zusätzlich eine neue Laufzeit oder einen unbefristeten Stand.

Vollständiges Löschen entfernt Vertragsstände, Preise, Änderungsprotokolle,
Erinnerungsaktionen und Importverknüpfungen des Eintrags. Der Kalender kann
alternativ Historie vor einem Datum entfernen: Die zu diesem Datum gültigen
Angaben bleiben als Berechnungsanker erhalten, alle älteren Preis-/Vertragsstände
und die Änderungsprotokolle, Erinnerungsaktionen und Importverknüpfungen dieses
Eintrags werden gelöscht. Das Datum wird als Untergrenze für neue Änderungen
behandelt. Ein rückwirkender Eintrag vor dieser Grenze wird abgewiesen.

Auszugsanalysen, deren gespeicherte Resultate, KI-Chats, KI-Brain, externe
Datensicherungen und Dateien auf anderen Geräten sind separate Datenbestände.
Diese müssen über ihre jeweiligen Funktionen bzw. Speicherorte gelöscht werden.
Die Kalenderaktion ist keine vollständige Löschung aller Kopien einer Person.

Alle Vertrags- und Kalenderendpunkte prüfen den angemeldeten Eigentümer. Die
Frontend-Filter dienen der Ansicht; sie ersetzen keine Berechtigungsprüfung.

## Migration und Sicherungen

Beim Start werden neue Spalten und die Tabelle `contract_versions` ergänzt.
Bestehende Einträge erhalten einmalig einen Ausgangsstand mit dem Marker
`history_assumed`. Vorhandene Preisperioden bleiben unverändert. Frühere
Metadatenänderungen wurden in alten Versionen nicht vollständig gespeichert;
der Ausgangsstand ist daher keine verifizierte Rekonstruktion vergangener
Zuordnungen. Solche Daten lassen sich bewusst rückwirkend ergänzen.

Benutzer-/Admin-JSON-Export enthält Vertragsstände, Archivierung und die
Historienuntergrenze (Schema 6). Beim Benutzerimport werden Katalog-IDs anhand
Namen/Scopes neu zugeordnet und die Eigentümerzuordnung auf den importierenden
Benutzer gesetzt. Historische Bezeichnungen bleiben erhalten. Die vorhandene
SQLite-Sicherung enthält alle neuen Daten ebenfalls. Alte JSON-Sicherungen
erhalten nach Import einen als übernommen markierten Ausgangsstand.

## API-Ergänzungen

- `GET /api/expenses?include_archived=true`: alle eigenen Einträge inklusive Archiv.
- `PUT /api/expenses/{id}`: `contract_effective_from`, `price_effective_from`,
  `contract_holder`; optional `update_price=false` für reine Metadatenänderungen.
- `GET /api/contracts/calendar?start=YYYY-MM-DD&end=YYYY-MM-DD`: eigene Zeitabschnitte,
  maximal 367 Tage zwischen 1900 und 2200, mit datierten Angaben und Zeitraumkosten.
- `POST /api/expenses/{id}/archive` und `/restore`.
- `POST /api/expenses/bulk` mit `action=delete`, `keep_history=true`: archivieren.
- `POST /api/expenses/{id}/history/purge` mit `{"before":"YYYY-MM-DD"}`.
- `DELETE /api/expenses/{id}/versions/{version_id}`: nur zukünftiger Vertragsstand.
- `DELETE /api/expenses/{id}/prices/{price_id}`: nur zukünftiger Preis.

Bestehende `DELETE /api/expenses/{id}`-Clients löschen weiterhin vollständig.
