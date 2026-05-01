# Annotation Guidelines

version: 3

## Purpose

The goal of annotation is to identify whether a document describes a persistent change that requires a geometric update in the TLM road network representation.

This is not about real world construction in general. It is about whether the TLM dataset would need to be updated because a mapped geometry must be added, removed, split, connected, disconnected, reshaped, or redrawn.

## Core Decision Question

Would a mapper need to add, remove, split, connect, disconnect, reshape, or redraw a geometry in TLM?

If yes:

tlm_relevant: true

If no:

tlm_relevant: false

If unclear:

tlm_relevant: false
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

## Core Label

tlm_relevant: true | false

A document is labeled true if it contains evidence of a persistent modification that requires changing TLM geometries.

A document is labeled false if the described change does not require changing TLM geometries.

## Optional Fields

review_required: true | false
notes: <free text>
change_type: topology | geometry | attribute_only | none

Use review_required: true for uncertain or borderline cases.

Use notes to briefly explain the decision.

Use change_type as follows:

* topology: network connectivity, axes, nodes, junctions, roundabouts, entries, exits, connections
* geometry: mapped geometry changes without clear network connectivity change
* attribute_only: only attribute change, no geometric update
* none: no relevant TLM update

## Primary Decision Rule

Label tlm_relevant: true if at least one of the following applies.

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

## Label false

Label tlm_relevant: false if all described changes can be handled without adding, removing, splitting, connecting, disconnecting, reshaping, or redrawing TLM geometries.

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

Set review_required: true when the document may indicate a TLM geometry update, but the evidence is insufficient.

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

Default for unclear cases:

tlm_relevant: false
review_required: true

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

### Pedestrian infrastructure

crossing only: false

crossing with new island: true

new pedestrian path as independent geometry: true

### Roundabouts

new roundabout: true

crossing replaced by roundabout: true

roundabout resurfaced: false

roundabout signalization changed: false

### Bridges

same alignment replacement: false

changed alignment: true

new bridge: true

bridge removed: true

replacement unclear: false + review_required

### Tunnels and underpasses

new tunnel or underpass: true

changed routing: true

same alignment maintenance: false

unclear replacement: false + review_required

### Traffic islands

physical island represented in TLM: true

painted island only: false

unclear: false + review_required

### Barriers and restrictions

temporary barrier: false

permanent barrier requiring a mapped point, split, or network information: true

restriction as sign only: false unless it requires a mapped object or split

### Belagsart

surface change only: false

new constructed path or road with geometry: true

unclear if only surface or new path: false + review_required

## Annotation Principles

### 1. Be conservative

Only label true when the document gives explicit evidence or a strong implication of a TLM geometry update.

### 2. Do not label construction activity itself

Construction work is only relevant if it creates, removes, or changes mapped TLM geometry.

### 3. Separate geometry from attributes

An attribute can be important in TLM but still not make the document geometrically relevant.

### 4. Ignore temporary context

Words such as the following usually indicate false:

* während Bauphase
* temporär
* provisorisch
* für die Dauer der Arbeiten
* Umleitung während der Bauzeit
* Baustellenverkehr

### 5. Prefer review over speculative true

If the document is plausible but ambiguous, use false with review.

## Examples

### True

document_text: "Die Kreuzung wird durch einen neuen Kreisel ersetzt."
tlm_relevant: true
review_required: false
change_type: topology
notes: "Intersection geometry and connectivity change."

document_text: "Zwischen den Quartieren wird ein neuer Fuss- und Veloweg gebaut."
tlm_relevant: true
review_required: false
change_type: topology
notes: "New independent network element."

document_text: "Im Kreuzungsbereich wird eine neue Mittelinsel erstellt."
tlm_relevant: true
review_required: false
change_type: geometry
notes: "New mapped traffic island."

document_text: "Die Strasse wird auf eine neue Linienführung verlegt."
tlm_relevant: true
review_required: false
change_type: topology
notes: "Road alignment changes."

### False

document_text: "Die Strasse wird saniert und der Belag ersetzt."
tlm_relevant: false
review_required: false
change_type: attribute_only
notes: "Maintenance and surface work only."

document_text: "Während der Bauphase wird der Verkehr umgeleitet."
tlm_relevant: false
review_required: false
change_type: none
notes: "Temporary traffic management."

document_text: "Ein Velostreifen wird auf der Fahrbahn markiert."
tlm_relevant: false
review_required: false
change_type: none
notes: "Painted marking only."

### False with review

document_text: "Die Hauptstrasse wird ausgebaut."
tlm_relevant: false
review_required: true
change_type: none
notes: "Ausbau is vague. No explicit geometry update."

document_text: "Die Brücke wird ersetzt."
tlm_relevant: false
review_required: true
change_type: none
notes: "Replacement is mentioned, but alignment change is unclear."

document_text: "Die Veloinfrastruktur wird verbessert."
tlm_relevant: false
review_required: true
change_type: none
notes: "Unclear whether this is a painted lane or a physically separated path."

## Output Format

document_id:
tlm_relevant: <true|false>
review_required: <true|false>
notes: <free text>
change_type: <topology|geometry|attribute_only|none>

## Versioning

Any change in labeling rules requires a version increment.

Version 3 defines tlm_relevant as a TLM geometry update requirement, not only as a topology change.