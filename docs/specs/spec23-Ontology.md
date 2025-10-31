# Ontology

| ID  | Short Name        | Description                                           | Category                |
|-----|-------------------|-------------------------------------------------------|-------------------------|
| 001 | posted            | user posted message (system; symbolic)                | Social                  |
| 002 | mentions          | mentions entity/concept                               | Social                  |
| 003 | states            | assertive factual claim (S states O)                  | Social                  |
| 004 | believes          | expresses belief/opinion about O                      | Social                  |
| 005 | asksAbout         | question/asks about O                                 | Social                  |
| 006 | cites             | references an external source (URL, paper)            | Social                  |
| 007 | joined            | joined/started membership/role                        | Social                  |
| 008 | left              | left/ended membership/role                            | Social                  |
| 009 | worksAt           | employment relationship                               | Social                  |
| 010 | livesIn           | location/habitation                                   | Social                  |
| 011 | hasEvent          | event mention (time-scoped)                           | Social                  |
| 012 | madeClaimAbout    | general claim relation (catch-all)                    | Social                  |
| 013 | disagreesWith     | contradiction/negation relation                       | Social                  |
| 014 | supports          | supports/endorses another claim or actor              | Social                  |
| 015 | securityAlert     | flagged content for security/moderation               | Social                  |
| 016 | follows           | social graph follows                                  | Social                  |
| 017 | followedBy        | inverse of follows                                    | Social                  |
| 018 | likes             | lightweight positive interaction                      | Social                  |
| 019 | reactsTo          | emoji/reaction engagement                             | Social                  |
| 020 | bookmarks         | saves message/entity for later                        | Social                  |
| 021 | blocks            | prevents another user from interacting                | Social                  |
| 022 | mutes             | hides content from another user                       | Social                  |
| 023 | relationshipType  | Type of relationship (adoptive, biological, etc.)     | Social                  |
| 024 | contradicts       | Information contradicts another assertion             | Social                  |
| 025 | owns              | entity owns an asset                                  | Identity & Ownership   |
| 026 | ownerOf           | inverse of owns                                       | Identity & Ownership   |
| 027 | identifiedBy      | entity mapped to identifier (email, DID, UUID)        | Identity & Ownership   |
| 028 | hasIdentifier     | general link to identifiers                           | Identity & Ownership   |
| 029 | createdBy         | created by actor                                      | Lifecycle & Provenance |
| 030 | createdAt         | creation timestamp                                    | Lifecycle & Provenance |
| 031 | modifiedBy        | modified by actor                                     | Lifecycle & Provenance |
| 032 | modifiedAt        | modification timestamp                                | Lifecycle & Provenance |
| 033 | deletedAt         | deletion timestamp                                    | Lifecycle & Provenance |
| 034 | archived          | marked as archived                                    | Lifecycle & Provenance |
| 035 | revoked           | revoked access/permission                             | Lifecycle & Provenance |
| 036 | deprecated        | marked as deprecated                                  | Lifecycle & Provenance |
| 037 | authorOf          | authored content                                      | Lifecycle & Provenance |
| 038 | editorOf          | edited content                                        | Lifecycle & Provenance |
| 039 | curatorOf         | curated content                                       | Lifecycle & Provenance |
| 040 | signedBy          | cryptographic signature reference                     | Lifecycle & Provenance |
| 041 | provenanceChain   | multi-step provenance                                 | Lifecycle & Provenance |
| 042 | derivedVia        | derived via transformation                            | Lifecycle & Provenance |
| 043 | supersedes        | Newer information replaces older assertion            | Lifecycle               |
| 044 | hasAttribute      | entity has a property or field                        | Structural Modeling    |
| 045 | hasMethod         | entity has an operation/function                      | Structural Modeling    |
| 046 | hasParameter      | method/function parameter                             | Structural Modeling    |
| 047 | subClassOf        | specialization (inheritance)                          | Structural Modeling    |
| 048 | instanceOf        | specific instance of type                             | Structural Modeling    |
| 049 | associatedWith    | general association                                   | Structural Modeling    |
| 050 | composedOf        | strong whole-part relationship                        | Structural Modeling    |
| 051 | aggregatedOf      | weaker whole-part relationship                        | Structural Modeling    |
| 052 | implements        | class realizes interface                              | Structural Modeling    |
| 053 | hasCardinality    | relationship cardinality                              | Structural Modeling    |
| 054 | dependsOn         | requires another element                              | Structural Modeling    |
| 055 | deployedOn        | artifact deployed to environment                      | Structural Modeling    |
| 056 | calls             | invokes another method                                | Behavioral             |
| 057 | triggers          | causes transition/action                              | Behavioral             |
| 058 | transitionsTo     | state changes to another                              | Behavioral             |
| 059 | sendsMessage      | sends message/signal                                  | Behavioral             |
| 060 | hasGuardCondition | condition guarding transition                         | Behavioral             |
| 061 | inputs            | action consumes data                                  | Behavioral             |
| 062 | outputs           | action produces data                                  | Behavioral             |
| 063 | precedes          | occurs before another                                 | Behavioral             |
| 064 | equivalentTo      | entities have same meaning                            | Ontological            |
| 065 | disjointWith      | entities cannot overlap                               | Ontological            |
| 066 | inverseOf         | reverse of another relation                           | Ontological            |
| 067 | hasDomain         | predicate domain                                      | Ontological            |
| 068 | hasRange          | predicate range                                       | Ontological            |
| 069 | subPropertyOf     | specialization of property                            | Ontological            |
| 070 | partOf            | general part-whole                                    | Ontological            |
| 071 | sameAs            | identifiers denote same                               | Ontological            |
| 072 | occursAt          | event occurs at time                                  | Temporal               |
| 073 | hasStartTime      | event start time                                      | Temporal               |
| 074 | hasEndTime        | event end time                                        | Temporal               |
| 075 | hasDuration       | event/process duration                                | Temporal               |
| 076 | before            | event before another                                  | Temporal               |
| 077 | after             | event after another                                   | Temporal               |
| 078 | during            | occurs within another                                 | Temporal               |
| 079 | overlapsWith      | temporal overlap                                      | Temporal               |
| 080 | hasRecurrence     | recurrence pattern                                    | Temporal               |
| 081 | hasTimestamp      | timestamp of claim/post                               | Temporal               |
| 082 | effectiveFrom     | When this information becomes valid                   | Temporal               |
| 083 | effectiveUntil    | When this information expires                         | Temporal               |
| 084 | locatedAt         | entity at specific location                           | Spatial                |
| 085 | hasCoordinates    | lat/long                                              | Spatial                |
| 086 | within            | contained within                                      | Spatial                |
| 087 | contains          | contains entity                                       | Spatial                |
| 088 | adjacentTo        | next to/bordering                                     | Spatial                |
| 089 | near              | nearby                                                | Spatial                |
| 090 | hasAddress        | postal/civic address                                  | Spatial                |
| 091 | hasPath           | spatial path                                          | Spatial                |
| 092 | origin            | starting point                                        | Spatial                |
| 093 | destination       | end point                                             | Spatial                |
| 094 | direction         | orientation                                           | Spatial                |
| 095 | trajectory        | spatial path over time                                | Spatiotemporal         |
| 096 | velocity          | speed and direction                                   | Spatiotemporal         |
| 097 | movementFromTo    | movement event                                        | Spatiotemporal         |
| 098 | occupies          | presence at location/time                             | Spatiotemporal         |
| 099 | isProcess         | entity is an ongoing process                          | Agency                 |
|100 | hasProcess        | involves a process                                    | Agency                 |
|101 | participatesIn    | actor participates in process                         | Agency                 |
|102 | initiates         | agent starts process                                  | Agency                 |
|103 | terminates        | agent ends process                                    | Agency                 |
|104 | intendsTo         | intention                                             | Agency                 |
|105 | attempts          | attempt (may fail)                                    | Agency                 |
|106 | causes            | causes event                                          | Agency                 |
|107 | causedBy          | caused by                                             | Agency                 |
|108 | resultedIn        | result of event                                       | Agency                 |
|109 | enables           | condition enables                                     | Agency                 |
|110 | prevents          | condition prevents                                    | Agency                 |
|111 | responsibleAgent  | accountable participant                               | Agency                 |
|112 | hasGoal           | entity has purpose                                    | Agency                 |
|113 | achieves          | action achieves goal                                  | Agency                 |
|114 | likelyTrue        | high probability                                      | Uncertainty            |
|115 | possibly          | possibly true                                         | Uncertainty            |
|116 | necessarily       | must be true                                          | Uncertainty            |
|117 | hasProbability    | numerical probability                                 | Uncertainty            |
|118 | hasConfidence     | confidence level                                      | Uncertainty            |
|119 | hasUncertainty    | uncertainty measure                                   | Uncertainty            |
|120 | errorMargin       | measurement error margin                              | Uncertainty            |
|121 | confidenceInterval| statistical confidence interval                       | Uncertainty            |
|122 | measurementMethod | how measured                                          | Uncertainty            |
|123 | confidence        | Confidence level (0.0-1.0)                            | Uncertainty            |
|124 | certaintyType     | Type of uncertainty (random, systematic, etc.)        | Uncertainty            |
|125 | hasMass           | physical mass                                         | Physical               |
|126 | hasVolume         | physical volume                                       | Physical               |
|127 | hasColor          | physical color                                        | Physical               |
|128 | hasTemperature    | temperature                                           | Physical               |
|129 | hasMaterial       | material composition                                  | Physical               |
|130 | hasState          | physical state (solid/liquid/gas)                     | Physical               |
|131 | hasValue          | literal value                                         | Data                   |
|132 | hasUnit           | unit of measure                                       | Data                   |
|133 | hasDataType       | literal data type                                     | Data                   |
|134 | minValue          | minimum value                                         | Data                   |
|135 | maxValue          | maximum value                                         | Data                   |
|136 | hasPrecision      | numerical precision                                   | Data                   |
|137 | hasHash           | hash of content                                       | Data                   |
|138 | contentAddressedBy| CID or hash pointer                                   | Data                   |
|139 | canonicalizedAs   | canonical form                                        | Data                   |
|140 | hashAlgorithm     | hash algorithm used                                   | Data                   |
|141 | canonicalizationMethod | method of canonicalization                       | Data                   |
|142 | verifiedBy        | verified by source/method                             | Security               |
|143 | trusts            | agent trusts entity                                   | Security               |
|144 | hasProvenance     | has provenance                                        | Security               |
|145 | hasIntegrity      | integrity check                                       | Security               |
|146 | hasAuthorization  | permission/authorization                              | Security               |
|147 | accessLevel       | access level (public, private, restricted)            | Security               |
|148 | visibility        | visibility setting                                    | Security               |
|149 | consentGiven      | consent provided                                      | Security               |
|150 | consentRevoked    | consent revoked                                       | Security               |
|151 | redacted          | content redacted                                      | Security               |
|152 | masked            | content masked                                        | Security               |
|153 | licenseUnder      | licensing of content                                  | Security               |
|154 | termsOfUse        | usage terms                                           | Security               |
|155 | compliesWith      | complies with policy                                  | Security               |
|156 | violatesPolicy    | violates policy                                       | Security               |
|157 | verifiedBy        | Method/entity that verified this                      | Security               |
|158 | accessLevel       | Who can see this metadata                             | Security               |
|159 | taggedWith        | tagged with keyword                                   | Metadata               |
|160 | annotatedBy       | annotated by actor                                    | Metadata               |
|161 | confidenceSource  | source of confidence score                            | Metadata               |
|162 | languageOf        | language of literal                                   | Metadata               |
|163 | localizedAs       | localized representation                              | Metadata               |
|164 | contextOf         | discourse or context                                  | Metadata               |
|165 | withinContext     | occurs within context                                 | Metadata               |
|166 | transfers         | transfer of ownership/value                           | Transactions           |
|167 | paidBy            | paid by agent                                         | Transactions           |
|168 | priceOf           | price of entity                                       | Transactions           |
|169 | ownsTitleTo       | owns title/rights                                     | Transactions           |
|170 | knows             | agent knows fact/agent                                | Social Knowledge       |
|171 | influences        | entity influences another                             | Social Knowledge       |
|172 | source            | Source of information (document, person, system)      | Provenance             |
|173 | evidence          | Supporting evidence for assertion                     | Provenance             |
|174 | legalBasis        | Legal foundation (court order, contract, etc.)        | Legal                  |
|175 | context           | Context where this assertion applies                  | Context                |
|176 | assumption        | Underlying assumption made                            | Logical                |
|177 | hasSex            | sex or gender identity                                | Social                 |
|178 | childOf           | child of parent (biological, adoptive, etc.)          | Social                 |
|179 | parentOf          | parent of child (biological, adoptive, etc.)          | Social                 |

## Label format enforcement

Label format enforcement: Labels SHOULD follow the canonical short-name style used in this ontology (camelCase or PascalCase where appropriate). Systems integrating with this ontology are encouraged to validate predicate labels for conformity during ingestion to ensure interoperability.

Example canonical label form (namespace-qualified):

	kind:namespace:label

For example: kind:person:parentOf or kind:org:worksAt

Grammar terms:

- Entities: `E:<namespace>:<label>`
- Relations: `R:<namespace>:<label>`
- Events: `EV:<namespace>:<label>`
- Literals: `L:<type>:<value>`

Notes:

- Short-form labels may still be used in some contexts, e.g. `::justLabel` for local-only labels.
- Labels may be accompanied by a content-address (sha1/sha256) or a human-readable description for provenance and matching purposes.