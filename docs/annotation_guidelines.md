# Annotation Guidelines

## Version

version: 2

---

## Purpose

The goal of annotation is to identify whether a document describes a **persistent structural change relevant for the TLM road network representation**.

This specifically refers to:

- changes in **network topology** (connectivity)
- changes in **explicit geometries represented in TLM**

This is **not about real-world construction in general**, but about whether the **TLM dataset must be updated**.

Temporary, operational, or purely descriptive changes are not relevant.

---

## Core Label

tlm_relevant: true | false

---

## Optional Review Signal (Recommended)

review_required: true | false  
notes: <string>  
change_type: topology | minor_geometry | none  

This field is used for **uncertain or borderline cases** that should be prioritized for manual review.

Typical reasons:

- unclear if topology is affected  
- vague project descriptions like "Ausbau"  
- replacement without geometric detail  
- possible reclassification of road type  

---

## Definition

A document is labeled **true** if it contains evidence of a **persistent modification that affects the TLM network representation**.

A document is labeled **false** if it only describes:

- maintenance  
- temporary measures  
- changes not represented in TLM  

---

## Decision Rules

### Label = true if ANY of the following applies

#### 1. Topology change (primary signal)

- new road or path  
- removed road  
- new connection between roads  
- rerouting or bypass  
- intersection rebuilt (e.g. crossing → roundabout)  
- new junction arms  

change_type: topology  

---

#### 2. New independent network elements

- new pedestrian path  
- new bike path (physically separated)  
- new bridge or tunnel with new alignment  

change_type: topology  

---

#### 3. Explicit geometric elements in TLM

- traffic islands (Mittelinseln)  
- new pedestrian crossing islands  
- separation structures creating new mapped geometry  

change_type: minor_geometry  

---

#### 4. Replacement with structural impact

- bridge replacement with changed alignment  
- tunnel replacement with changed routing  

If unclear → review_required: true  

---

### Label = false if ALL of the following apply

#### 1. Maintenance or surface work

- resurfacing  
- pavement replacement  
- markings  
- drainage  
- lighting  
- noise reduction without geometry change  

---

#### 2. Width or layout changes without topology

- road widening or narrowing  
- additional lane within same alignment  
- bike lane painted on road  

Important:  
TLM roads are modeled as **centerlines with typification**, not width.

---

#### 3. External systems (not part of TLM road network)

- bus stops  
- public transport infrastructure  
- signalisation  

---

#### 4. Temporary changes

- construction phases  
- road closures  
- detours  
- temporary traffic management  

---

#### 5. Administrative or planning content

- funding decisions  
- political processes  
- early planning without defined geometry  

---

## Critical Edge Cases

- Bridge replacement  
  same alignment → false  
  new alignment → true  

- Road widening  
  width only → false  
  potential reclassification → review_required: true  

- Bike infrastructure  
  painted lane → false  
  separated path → true  

- Pedestrian infrastructure  
  crossing only → false  
  crossing with island → true  

---

## Annotation Principles

### 1. Be conservative

If unsure → false + review_required: true  

---

### 2. Require explicit evidence

Do not infer structural change unless clearly stated or strongly implied.

---

### 3. Ignore temporary context

Words like:

- während Bauphase  
- temporär  
- für die Dauer der Arbeiten  

indicate false.

---

### 4. Focus on TLM relevance

Ask:

Would this change the **centerline graph or node structure** in TLM?

- yes → true  
- no → false  

---

## Examples

### True

- Die Kreuzung wird durch einen Kreisel ersetzt  
- Neue Verbindung zwischen zwei Strassen wird erstellt  
- Ein neuer Veloweg wird gebaut (separat geführt)  

---

### False

- Die Strasse wird saniert  
- Belag wird ersetzt  
- Markierungen werden erneuert  
- Verkehrsführung während Bauphase  

---

### True + Review Required

- Brücke wird ersetzt (keine Details zur Geometrie)  
- Ausbau angekündigt, aber unklar ob Topologie betroffen ist  

---

## Output Format

document_id: <string>  
tlm_relevant: <true|false>  
review_required: <true|false>  
notes: <string>  
change_type: <topology|minor_geometry|none>  

---

## Versioning

Any change in labeling rules requires a version increment.