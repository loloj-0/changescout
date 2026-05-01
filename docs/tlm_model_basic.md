# TLM Model Basics for ChangeScout MVP

version: 1

## Purpose

This document explains the minimal TLM road model assumptions needed for consistent annotation in the ChangeScout MVP.

It is not a full summary of the TLM capture guidelines. It only covers concepts that affect the binary label tlm_relevant.

The annotation label asks:

Would a mapper need to add, remove, split, connect, disconnect, reshape, or redraw a geometry in TLM?

## MVP Scope

The MVP focuses on road construction and civil engineering changes related to Topic Strassen und Wege.

Relevant TLM concepts:

* road axes
* path axes
* network edges
* network nodes
* connections
* entries and exits
* roundabouts
* physically separated pedestrian or cycling infrastructure
* road related engineering structures
* selected road related mapped objects such as traffic islands

Other TLM topics are only relevant if the document clearly implies a road network geometry update.

## 1. Roads and paths are modeled as axes

In TLM, roads and paths are primarily represented by axes.

For non direction separated roads, the axis is normally captured in the middle of the road body.

For direction separated roads, two parallel, oppositely directed edges can be represented.

This means:

* the mapped geometry is not the full road surface
* width alone is not the main geometry
* number of lanes alone is not the geometry
* a construction project is not automatically relevant

Annotation consequence:

A road widening on the same alignment is usually false.

A road widening that creates direction separated axes, a new connection, or a changed alignment is true.

## 2. Object forming attributes can cause segmentation

TLM road axes can be segmented when an object forming attribute changes.

Relevant object forming properties include:

* Objektart
* Verkehrsbeschraenkung
* Kunstbaute
* Richtungsgetrennt
* Belagsart
* Kreisel
* Befahrbarkeit

Annotation consequence:

An attribute change alone is not automatically tlm_relevant: true.

It becomes relevant when the document indicates that geometry must be split, redrawn, or otherwise changed.

Examples:

Belag wird ersetzt: false

neuer Weg mit Hartbelag wird gebaut: true

Abschnitt wird baulich richtungsgetrennt: true

Verkehrsbeschränkung geändert: false unless a permanent mapped point or split is required

## 3. Width is not the same as geometry

TLM uses road width for classification and segmentation. The road axis is still the central modeled geometry.

Relevant thresholds from the TLM guidance include:

* road widening segment: more than 50 m
* axis change: more than 2 m
* distance between road nodes in crossing area: 2 m
* parallel axes: more than 100 m
* traffic island width: more than 8 m
* central island or green strip length: more than 50 m
* connection object: more than 50 cm
* distance between engineering structure and junction: more than 50 cm

Annotation consequence:

A pure width change is normally false.

A width change becomes true only if it causes a mapped geometry update, such as a new separate axis, changed alignment, new connection, or mapped traffic island.

## 4. Direction separated roads are important

Direction separated roads are modeled differently from normal roads.

A road can become relevant when a project creates:

* physically separated carriageways
* two separate directional axes
* ramps
* entries
* exits
* connections between separated axes and other roads

Annotation consequence:

Generic "road widening" is not enough.

Explicit physical directional separation is true.

## 5. Network topology

TLM uses network nodes and connections to represent road network topology.

Relevant concepts:

* road and path junctions
* motorway and autostrasse entries
* motorway and autostrasse exits
* junctions between high capacity roads
* connections where axes do not directly intersect
* standard nodes at road and path junctions, class changes, and road ends
* loop junctions for closed loops

Annotation consequence:

A document is true if it describes new, removed, or changed network connectivity.

Examples:

crossing becomes roundabout: true

new junction arm: true

new access road: true

same road resurfaced through a junction: false

## 6. Roundabouts are relevant

A roundabout is a road network node and geometry case.

A new roundabout or replacement of an intersection by a roundabout requires geometry and topology updates.

Annotation consequence:

new roundabout: true

crossing replaced by roundabout: true

roundabout maintenance only: false

## 7. Parallel axes and separated slow traffic infrastructure

TLM can represent parallel axes for slow traffic when they are physically separated from the main axis.

Relevant examples:

* separated bike path
* separated pedestrian path
* separated bike and pedestrian path
* parallel slow traffic axis along a road

Not enough:

* painted bike lane
* painted road markings
* bike lane without physical separation
* adjacent sidewalk unless represented as a separate relevant axis according to TLM rules

Annotation consequence:

physically separated bike path: true

painted bike lane: false

vague "improved cycling infrastructure": false + review_required

## 8. Traffic islands and separation structures can be geometry

Some local objects are relevant because they are explicitly represented as TLM geometry.

Examples:

* traffic island
* central island
* pedestrian crossing island
* physical separation structure

Annotation consequence:

physical island represented in TLM: true

painted island only: false

unclear island type: false + review_required

## 9. Road related engineering structures

Road related engineering structures can be relevant when they are mapped as part of the road axis or require geometry changes.

Relevant examples:

* bridge
* tunnel
* underpass
* gallery
* ford
* stair
* road axis in or on a building
* road axis on a dam or retaining structure
* road related pier or landing connection for ferry cases

Annotation consequence:

new structure with road axis: true

removed structure affecting road axis: true

replacement with changed alignment: true

same alignment replacement: false

unclear replacement: false + review_required

## 10. Attributes and restrictions are not automatically geometry

TLM contains important road attributes and restrictions.

Examples:

* Befahrbarkeit
* Belagsart
* Verkehrsbeschraenkung
* Allgemeine Verkehrsbeschraenkung
* Eigentümer
* Name
* routes
* opening date

These are not automatically geometry changes.

Annotation consequence:

surface becomes asphalt: false if only the surface changes

road becomes restricted: false if only signage or access rule changes

permanent barrier requiring a mapped network point: true

temporary closure: false

## 11. Temporary changes are outside the MVP label

Temporary traffic arrangements are not relevant for tlm_relevant.

Examples:

* detour during construction
* temporary closure
* temporary one way traffic
* temporary pedestrian routing
* temporary provisional bridge or access

Annotation consequence:

Temporary construction context should be ignored unless the final permanent state requires TLM geometry updates.

## 12. Areas and parking areas are usually out of scope

Traffic areas, private driving areas, parking areas, industrial areas, and residential areas can contain roads or access axes.

For MVP annotation, they are only relevant if the document clearly describes a mapped road axis, access, connection, or independently represented road geometry.

Annotation consequence:

new parking area alone: false

new access road to parking area: true

new marked parking fields: false

new clearly mapped road axis inside a traffic area: true

## 13. Public transport is mostly out of scope

Public transport infrastructure is not part of the MVP unless it directly changes road geometry.

Examples:

bus stop only: false

service change: false

tram track affecting road axes: review_required or true if explicit road geometry changes

new road axis due to tram separation: true

## 14. Conservative interpretation

The TLM model is more selective than real world construction.

Not every built object becomes a TLM geometry.

Not every important infrastructure project requires a TLM geometry update.

Annotation should therefore be conservative.

Default for unclear documents:

tlm_relevant: false
review_required: true

## Practical Checklist

Before labeling true, ask:

1. Is there a persistent final state?
2. Is a TLM geometry explicitly or strongly implied?
3. Would a mapper need to add, remove, split, connect, disconnect, reshape, or redraw something?
4. Is it more than temporary traffic management?
5. Is it more than surface work, markings, signage, or attribute change?

If all relevant answers support a geometry update, label true.

If not, label false.

If unclear, label false with review.