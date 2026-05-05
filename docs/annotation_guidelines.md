# Annotation Guidelines

version: 4

## Purpose

The goal of annotation is to identify whether a source describes a persistent change that requires a geometric update in the TLM road network representation.

This is not about real world construction in general. It is about whether the TLM dataset would need to be updated because a mapped geometry must be added, removed, split, connected, disconnected, reshaped, or redrawn.

The annotation is based on the source text itself. Do not infer confirmed TLM relevance from project importance, general construction wording, political relevance, or expected future development unless the text contains sufficient geometric evidence.

## Core Decision Question

Would a mapper need to add, remove, split, connect, disconnect, reshape, or redraw a geometry in TLM based on the information in this source?

If yes:

tlm_relevant: true
review_required: false

If no and the source has no plausible TLM geometry signal:

tlm_relevant: false
review_required: false

If the source contains plausible TLM geometry signals but the evidence is insufficient:

tlm_relevant: false
review_required: true

The combination below is invalid:

tlm_relevant: true
review_required: true

## MVP Scope

The MVP focuses on road construction and civil engineering changes affecting the TLM topic Strassen und Wege.

Included:

* roads
* paths
* road network edges
* road network nodes
* connections
* roundabouts
* entries and exits
* physically separated cycling or pedestrian infrastructure
* road related engineering structures
* road related mapped geometries such as traffic islands

Out of scope for the MVP unless they directly affect the road network geometry:

* buildings
* public transport stops
* purely administrative road information
* routing tables without geometry changes
* planning without concrete geometric evidence
* temporary traffic management

## Core Labels

### tlm_relevant

tlm_relevant: true | false

A source is labeled true if it contains sufficient evidence of a persistent modification that requires changing TLM geometries.

A source is labeled false if the described change does not require changing TLM geometries, or if the source only suggests possible TLM relevance without sufficient evidence.

tlm_relevant answers:

Is the TLM geometry update sufficiently confirmed or strongly implied by this source text?

### review_required

review_required: true | false

Use review_required: true when the source contains plausible TLM geometry signals, but the source text does not provide enough evidence to label it as confirmed TLM relevant.

review_required answers:

Should a human reviewer check this source because it may become or indicate a TLM relevant change?

Typical review cases are planning studies, concepts, variants, BGK processes, vague road redesigns, unclear bridge replacements, unclear cycling infrastructure, or future measures that are not yet fixed as concrete implementation.

### notes

notes: <free text>

Use notes to briefly explain the decision.

For tlm_relevant: true, the note must name the concrete TLM trigger.

Good examples:

* New roundabout replaces existing intersection and changes network connectivity.
* New underpass creates an independent path connection below the road.
* Extended motorway entry lane changes permanent access geometry.
* New pedestrian crossing island creates mapped local geometry.

For review_required: true, the note must name the plausible signal and the missing evidence.

Good examples:

* BGK discusses conversion of roundabouts to signal controlled junctions, but no concrete implementation is confirmed.
* Bridge replacement is mentioned, but the text does not state whether the alignment changes.
* Cycling infrastructure is planned, but the text does not clarify whether it is physically separated.

For tlm_relevant: false and review_required: false, the note should state why no TLM geometry update is expected.

Good examples:

* Road resurfacing and drainage works only.
* Temporary traffic management during construction only.
* Bus stop and timetable changes without road geometry update.

### change_type

change_type: topology | geometry | attribute_only | none

Use change_type as follows:

* topology: network connectivity, axes, nodes, junctions, roundabouts, entries, exits, connections
* geometry: mapped geometry changes without clear network connectivity change
* attribute_only: only attribute change, no geometric update
* none: no relevant TLM update

For review_required: true, use change_type: none unless the source clearly confirms the type of future TLM change. The review label already expresses that the geometric evidence is insufficient.

## Derived Label

### triage_class

triage_class is derived from tlm_relevant and review_required.

| tlm_relevant | review_required | triage_class |
|---|---|---|
| true | false | confirmed_relevant |
| false | true | needs_review |
| false | false | not_relevant |
| true | true | invalid |

### confirmed_relevant

The source contains sufficient evidence for a persistent TLM geometry update.

Use for confirmed new or changed roads, paths, junctions, roundabouts, entries, exits, underpasses, bridges with geometric effect, or explicit mapped geometries such as traffic islands.

### needs_review

The source contains plausible TLM geometry signals, but the evidence is insufficient for confirmed relevance.

Use for concepts, studies, variants, early planning, vague road redesigns, possible but unclear bridge replacements, unclear cycling infrastructure, and future measures not yet fixed as concrete implementation.

### not_relevant

The source contains no plausible TLM geometry update, or describes only maintenance, surface work, markings, operational changes, temporary traffic management, administrative content, or external systems without road geometry effect.

## Evaluation Use

For strict binary relevance evaluation:

* Use confirmed_relevant as positive.
* Use not_relevant as negative.
* Exclude needs_review.

For actionable lead evaluation:

* Use confirmed_relevant and needs_review as positive.
* Use not_relevant as negative.

For three class triage evaluation:

* Use confirmed_relevant, needs_review, and not_relevant.

## Primary Decision Rule

Label tlm_relevant: true if at least one of the following applies and the source text gives sufficient evidence.

### 1. New, removed, or redrawn road network geometry

Use change_type: topology.

Examples:

* new road
* new path
* removed road or path
* permanently closed and removed road or path
* rerouting
* bypass
* changed road alignment
* road moved to a new route
* new access road
* new connection between existing roads
* road network gap closed by a new road element

### 2. Changed network connectivity

Use change_type: topology.

Examples:

* new junction
* removed junction
* rebuilt intersection
* crossing replaced by roundabout
* new roundabout
* new junction arms
* new entry or exit
* changed motorway or autostrasse access
* new or changed connection object
* road split or merged due to directional separation

### 3. New or changed independent network elements

Use change_type: topology.

Examples:

* new physically separated bike path
* new physically separated pedestrian path
* new combined bike and pedestrian path
* new parallel slow traffic axis
* new path that connects to the existing network
* new road or path in a traffic area if it is independently represented as an axis

Important:

A painted bike lane on the existing carriageway is not enough. The infrastructure must require a separate mapped geometry.

### 4. New or changed explicit TLM geometry

Use change_type: geometry.

Examples:

* new traffic island
* new pedestrian crossing island
* new central island
* new separation structure that is explicitly represented in TLM
* new or changed road related mapped geometry that must be drawn independently

Important:

Only label true if the element must be represented as geometry in TLM. Painted markings alone are not enough.

### 5. Road related engineering structures with geometric effect

Use change_type: topology if the road axis or connectivity changes.

Use change_type: geometry if only the mapped engineering structure changes.

Examples:

* new bridge
* bridge removed
* bridge replacement with changed alignment
* new tunnel
* tunnel replacement with changed routing
* new underpass
* new gallery
* new ford
* new road related stair connection
* road axis on or through a structure changes

If a bridge, tunnel, underpass, or gallery is replaced in the same location without evidence of changed road geometry, label false and set review_required: true only if the text suggests possible alignment changes.

### 6. Attribute changes that imply geometry splitting or redrawing

Use change_type: topology or geometry, depending on the case.

Examples:

* road becomes physically direction separated and therefore needs separate axes
* axis change greater than the relevant TLM threshold is explicitly described
* road is split into differently represented sections because an object forming property changes and geometry segmentation is required
* a permanent barrier or restriction requires a network point or split

Important:

Do not infer this from generic wording like "Ausbau". Require explicit evidence or strong implication.

## Label False

Label tlm_relevant: false if the source does not provide sufficient evidence that a TLM geometry must be added, removed, split, connected, disconnected, reshaped, or redrawn.

### 1. Maintenance or surface work

Examples:

* road maintenance
* resurfacing
* pavement replacement
* repair
* drainage works
* lighting
* noise reduction without geometric change
* retaining work without road geometry change

### 2. Width or layout changes without geometric redraw

Examples:

* road widening on the same alignment
* road narrowing on the same alignment
* additional lane within the same mapped axis
* turning lane within the same mapped axis
* bus lane within the same mapped axis
* road classification changes based only on width

Important:

TLM roads are represented as axes. Width alone is not sufficient for tlm_relevant: true.

### 3. Markings and painted infrastructure

Examples:

* new road markings
* painted bike lane
* painted bus lane
* pedestrian crossing without island
* parking markings
* lane markings
* signalization markings

### 4. Pure attribute changes

Examples:

* Belagsart change only
* Befahrbarkeit change only
* Verkehrsbeschraenkung change only
* Eigentümer change only
* name change only
* road route classification only
* opening date only

If an attribute change also requires geometry splitting, set review_required: true unless the geometric implication is explicit.

### 5. Temporary or operational changes

Examples:

* construction phase
* temporary detour
* temporary closure
* temporary traffic management
* temporary signalization
* traffic guidance during works
* temporary bridge or provisional route used only during construction

### 6. Administrative or planning content

Examples:

* funding decision
* political approval
* public consultation
* project study
* strategy
* early planning without defined geometry
* announcement without concrete spatial change

Planning content can still be review_required: true if it describes plausible future TLM geometry changes but does not yet confirm implementation.

### 7. External systems without road geometry update

Examples:

* bus stops
* public transport service changes
* traffic lights
* signage
* operational traffic rules
* parking regulations
* speed limits

## Review Required

Set review_required: true when the source may indicate a TLM geometry update, but the evidence is insufficient for confirmed relevance.

review_required: true always implies:

tlm_relevant: false

Typical cases:

* "Ausbau" without details
* "Umgestaltung" without clear geometry
* "Sanierung Brücke" without alignment information
* "Ersatz Brücke" without indication whether alignment changes
* "Verbesserung Veloinfrastruktur" without physical separation
* "neue Verkehrsführung" without clear permanence or geometry
* "Knoten wird angepasst" without details
* "Strasse wird verbreitert" where directional separation or new access could be implied but is not stated
* "Belag wird geändert" where a new mapped path or axis could also be implied but is not stated
* concept, study, BGK, forum, synthesis variant, public participation, or preliminary project with plausible TLM relevant measures
* future construction program where individual projects are not yet defined
* bridge, underpass, junction, or cycling measure mentioned without enough detail

Default for unclear but plausible cases:

tlm_relevant: false
review_required: true
change_type: none

Default for unclear and not plausible cases:

tlm_relevant: false
review_required: false
change_type: none

## Critical Edge Cases

### Road widening

same alignment, same centerline, no new mapped object: false

widening plus physical directional separation: true

widening plus new access, roundabout, or junction arms: true

widening only described as "Ausbau": false + review_required

### Road narrowing

same alignment: false

permanent redesign that changes the mapped axis or creates a new mapped structure: true

unclear: false + review_required

### Lane additions

additional lane within same mapped axis: false

new physically separated carriageway: true

new entry, exit, or separated ramp: true

### Bike infrastructure

painted bike lane: false

physically separated bike path: true

bike path unclear: false + review_required

Bus plus bike lane on the existing carriageway is usually false unless it creates a separate mapped axis or changes network geometry.

### Pedestrian infrastructure

crossing only: false

crossing with new island: true

new pedestrian path as independent geometry: true

new underpass or overpass for pedestrians: true

unclear future crossing solution: false + review_required

### Roundabouts

new roundabout: true

crossing replaced by roundabout: true

roundabout replaced by another junction form: true if implementation is confirmed

roundabout resurfaced: false

roundabout signalization changed: false

roundabout conversion only discussed in a concept or BGK: false + review_required

### Bridges

same alignment replacement: false

changed alignment: true

new bridge: true

bridge removed: true

replacement unclear: false + review_required

bridge widening alone: false unless road axis, connectivity, or mapped geometry changes are stated

### Tunnels and underpasses

new tunnel or underpass: true

changed routing: true

same alignment maintenance: false

unclear replacement: false + review_required

underpass closure or replacement by surface crossing: true if permanent pedestrian or road network geometry changes are confirmed

### Traffic islands

physical island represented in TLM: true

painted island only: false

unclear: false + review_required

new pedestrian crossing with Mittelinsel or Schutzinsel: true if implementation is confirmed

### Barriers and restrictions

temporary barrier: false

permanent barrier requiring a mapped point, split, or network information: true

restriction as sign only: false unless it requires a mapped object or split

### Belagsart

surface change only: false

new constructed path or road with geometry: true

unclear if only surface or new path: false + review_required

### Motorway entries and exits

new entry or exit: true

removed entry or exit: true

reopened entry or exit: true if it changes usable permanent network connectivity and is linked to physical works

reopened entry or exit only as administrative release without physical geometry change: false + review_required

entry or exit lane extended: true if permanent access geometry changes

### Planning status

confirmed construction project with concrete geometry evidence: true

concept, study, forum, synthesis variant, preliminary project, or public participation: false + review_required if plausible TLM signals exist

general strategy or program without concrete geometry evidence: false

future construction program where individual projects are not yet defined: false + review_required if plausible TLM signals exist

## Annotation Principles

### 1. Be conservative

Only label true when the source gives explicit evidence or a strong implication of a TLM geometry update.

### 2. Do not label construction activity itself

Construction work is only relevant if it creates, removes, or changes mapped TLM geometry.

### 3. Separate geometry from attributes

An attribute can be important in TLM but still not make the source geometrically relevant.

### 4. Ignore temporary context

Words such as the following usually indicate false:

* während Bauphase
* temporär
* provisorisch
* für die Dauer der Arbeiten
* Umleitung während der Bauzeit
* Baustellenverkehr

### 5. Prefer review over speculative true

If the source is plausible but ambiguous, use false with review.

### 6. Use the whole source

Always judge the full source text. Important evidence can occur late in the source, for example in measure lists, project descriptions, or linked media release summaries.

### 7. One confirmed signal is enough

If a source contains several sections and at least one section clearly confirms a TLM geometry update, label the whole source as tlm_relevant: true.

The note must name the concrete confirmed signal.

Example:

A source contains general road widening, bus lanes, and resurfacing, but later states that a motorway entry lane will be extended. The source is tlm_relevant: true because the entry lane extension affects permanent access geometry.

### 8. Notes must explain the label

Notes are not general summaries. They must explain why the source received its label.

For true labels, state the concrete geometry or topology trigger.

For review labels, state the plausible signal and the missing evidence.

For false labels, state why the source does not imply a TLM geometry update.

## Examples

### True

document_text: "Die Kreuzung wird durch einen neuen Kreisel ersetzt."
tlm_relevant: true
review_required: false
change_type: topology
notes: "Intersection is replaced by a new roundabout, changing geometry and network connectivity."

document_text: "Zwischen den Quartieren wird ein neuer Fuss- und Veloweg gebaut."
tlm_relevant: true
review_required: false
change_type: topology
notes: "New independent foot and cycle path creates a separate network element."

document_text: "Im Kreuzungsbereich wird eine neue Mittelinsel erstellt."
tlm_relevant: true
review_required: false
change_type: geometry
notes: "New pedestrian crossing island creates mapped local geometry."

document_text: "Die Strasse wird auf eine neue Linienführung verlegt."
tlm_relevant: true
review_required: false
change_type: topology
notes: "Road is moved to a new alignment and must be redrawn."

document_text: "Die Einfahrspur zum Autobahnanschluss wird verlängert."
tlm_relevant: true
review_required: false
change_type: topology
notes: "Extended motorway entry lane changes permanent access geometry."

### False

document_text: "Die Strasse wird saniert und der Belag ersetzt."
tlm_relevant: false
review_required: false
change_type: attribute_only
notes: "Maintenance and surface replacement only."

document_text: "Während der Bauphase wird der Verkehr umgeleitet."
tlm_relevant: false
review_required: false
change_type: none
notes: "Temporary traffic management during construction only."

document_text: "Ein Velostreifen wird auf der Fahrbahn markiert."
tlm_relevant: false
review_required: false
change_type: none
notes: "Painted bike lane on existing carriageway only."

document_text: "Die Bushaltestelle wird gemäss BehiG angepasst."
tlm_relevant: false
review_required: false
change_type: none
notes: "Bus stop accessibility upgrade without road network geometry update."

### False with review

document_text: "Die Hauptstrasse wird ausgebaut."
tlm_relevant: false
review_required: true
change_type: none
notes: "Ausbau is vague and no concrete geometry update is stated."

document_text: "Die Brücke wird ersetzt."
tlm_relevant: false
review_required: true
change_type: none
notes: "Bridge replacement is mentioned, but alignment or network effect is unclear."

document_text: "Die Veloinfrastruktur wird verbessert."
tlm_relevant: false
review_required: true
change_type: none
notes: "Cycling improvement is plausible, but physical separation or new path geometry is unclear."

document_text: "Im BGK wird die Umgestaltung mehrerer Knoten geprüft."
tlm_relevant: false
review_required: true
change_type: none
notes: "BGK discusses possible junction redesigns, but no concrete implementation is confirmed."

document_text: "Eine Synthesevariante sieht die Umwandlung von Kreiseln in ampelgesteuerte Knoten vor."
tlm_relevant: false
review_required: true
change_type: none
notes: "Variant discusses future roundabout conversion, but the project is not yet confirmed as implementation."

## Output Format

document_id:
tlm_relevant: <true|false>
review_required: <true|false>
notes: <free text>
change_type: <topology|geometry|attribute_only|none>
triage_class: <confirmed_relevant|needs_review|not_relevant|invalid>

## Versioning

Any change in labeling rules requires a version increment.

Version 3 defined tlm_relevant as a TLM geometry update requirement, not only as a topology change.

Version 4 freezes the evaluation schema for the expanded annotation dataset. It defines review_required as a separate uncertainty and triage signal, disallows the combination tlm_relevant: true with review_required: true, and defines the derived triage_class label for evaluation.