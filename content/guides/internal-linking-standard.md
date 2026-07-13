# CargoPT Internal Linking Standard v1

## Purpose

This document defines the Source of Truth for internal links between
CargoPT guide articles.

The objective is to build a useful navigation network rather than a
star graph where most articles point to the same one or two pages.

## Scope

The standard applies to:

- `content/guides/articles/*.json`;
- the `related_links` field;
- new Portuguese guide articles.

It does not replace contextual links that may later be added inside
article sections.

## Core requirements

Every structured article must:

1. contain exactly four `related_links`;
2. contain no duplicate destination;
3. contain no self-link;
4. link to at least two structured articles;
5. receive at least two incoming links from structured articles;
6. avoid linking only to the same commercial hub;
7. avoid becoming a dead end;
8. use only registry paths, verified static pages, or the request form;
9. use `/#request` as the standard conversion destination;
10. preserve a clear topical relationship between source and target.

## Link type rules

The destination determines the link type:

- registry topic with `published` status → `guide`;
- registry topic with `planned` status and JSON → `planned`;
- registry topic with `existing_landing` status → `landing`;
- request form → `service`;
- verified guides hub → `parent`.

## Canonical link map model

The internal link map is the canonical Source of Truth for target selection,
relationship semantics, and display order. Article JSON files are rendered
outputs of that map and must not become an independent editorial source.

Each source article maps to exactly four ordered relationship objects:

    "article-id": [
      {
        "target": "target-id",
        "reason": "same_cluster",
        "priority": 1
      },
      {
        "target": "target-id",
        "reason": "next_step",
        "priority": 2
      },
      {
        "target": "target-id",
        "reason": "authority",
        "priority": 3
      },
      {
        "target": "@request",
        "reason": "conversion",
        "priority": 4
      }
    ]

Each relationship object has exactly three fields:

- `target`: a registry topic id or the reserved `@request` id;
- `reason`: one value from the controlled relationship vocabulary;
- `priority`: the positive integer that defines display order.

The schema v1 list of target ids is transitional. It may be accepted only by
migration tooling operating in an explicit transitional mode. After the map
migration, all editorial changes must use the canonical object model.

## Relationship reasons

The controlled `reason` vocabulary is:

- `next_step`: the destination is the natural next action in the reader journey;
- `dependency`: the source task depends on information in the destination;
- `same_cluster`: the destination provides closely related coverage in the same cluster;
- `authority`: the destination is a broader or foundational guide that strengthens context;
- `commercial`: the destination is a directly relevant commercial landing;
- `conversion`: the destination is the primary request endpoint;
- `prerequisite`: the destination should be understood or completed before the source task.

Every source article must satisfy all of these relationship rules:

- exactly one relationship has reason `conversion`;
- `conversion` may target only `@request`;
- `@request` may appear only with reason `conversion`;
- at least one relationship has reason `same_cluster`;
- at least one relationship has reason `next_step`, `dependency`, or `prerequisite`;
- at most one relationship has reason `authority`;
- at most one relationship has reason `commercial`;
- reasons are unique within one source article.

## Priority rules

Priorities are editorial data, not implementation metadata.

- priorities are integers;
- priorities start at `1`;
- priorities are unique within one source article;
- priorities are continuous with no gaps;
- the serialized relationship order must match ascending priority order;
- lower numbers are rendered before higher numbers;
- changing priority is an editorial ordering change and must pass the same review as changing a target.

With exactly four relationships, the only valid priority set is:

    1, 2, 3, 4

## Canonical map validation

The canonical map validator must be read-only and fail with a non-zero exit
code before any article files are written.

It must verify:

- the map schema version is supported;
- map source ids exactly match the structured article corpus;
- every source contains exactly four relationship objects;
- every relationship object contains exactly `target`, `reason`, and `priority`;
- every target is a non-empty string;
- every reason belongs to the controlled vocabulary;
- every priority is an integer that satisfies the priority rules;
- serialized order matches ascending priority order;
- targets are unique within one source article;
- no source targets itself;
- every target resolves through the registry or the reserved `@request` target;
- all relationship reason rules pass;
- graph quality gates are evaluated after per-source validation succeeds.

Incoming and outgoing article-link graph gates count only article targets.
Service and commercial landing targets do not count as article graph edges.

Validation failure must produce no map rewrite, no article rewrite, and no
partial output.

The type must reflect the destination Source of Truth, not the URL shape.

## Cluster templates

### Cities

Each city article links to:

1. one nearby or contextually related city;
2. a second nearby or contextually related city;
3. one relevant price article;
4. the request form.

City pages must form regional rings and must not remain orphan pages.

### Planning

Each planning article links to:

1. the previous related planning step;
2. the next related planning step;
3. one relevant article from packing, prices, objects, or rights;
4. the request form.

Planning links should follow the user journey from preparation to
booking and execution.

### Packing

Each packing article links to:

1. one related packing article;
2. a second related packing article;
3. one relevant planning, object, or rights article;
4. the request form.

### Objects

Each object article links to:

1. one closely related object article;
2. a second closely related object article;
3. one relevant packing, planning, prices, or rights article;
4. a relevant service landing or the request form.

### Prices

Each price article links to:

1. one related price article;
2. a second related price article;
3. one relevant planning, city, or object article;
4. a relevant landing or the request form.

Price articles must redistribute internal authority instead of only
receiving links.

### Rights

Each rights article links to:

1. one related rights article;
2. a second rights article;
3. one relevant planning, packing, or object article;
4. the request form.

## Deterministic relationship generation

Canonical relationship selection must be deterministic. Given the same
registry, article corpus, explicit editorial relations, and batch topic ids,
the generated relationship plan must be identical.

The selection order is:

1. explicit editorial relation from the registry or an approved batch plan;
2. geographic or semantic proximity defined by the cluster rules;
3. deterministic cluster-ring fallback.

Random selection and dependence on filesystem iteration order are prohibited.

### Required relationship layout

Every source uses this ordered layout:

1. `same_cluster`;
2. one journey reason: `next_step`, `dependency`, or `prerequisite`;
3. `authority` or `commercial`;
4. `conversion` targeting `@request`.

`next_step` is the default journey reason.

Use `dependency` only when the source task depends on information in the
destination.

Use `prerequisite` only when the destination should be understood or completed
before the source task.

Use `authority` for an informational guide that supplies broader, foundational,
price, planning, safety, packing, or object context.

Use `commercial` only for a separate transactional landing that is directly
relevant to the source. A commercial landing does not replace the
`@request` conversion relationship.

### City selection algorithm

For a city source, choose `same_cluster` using this precedence:

1. the same metropolitan or functional area;
2. the nearest major city represented in the corpus;
3. a city with a similar moving context;
4. the next city in the deterministic city ring.

Choose the journey target using this precedence:

1. a directly relevant route article;
2. a regional price article;
3. a preparation or planning article;
4. another city article that represents a natural next step.

Choose the third relationship using this precedence:

1. a dedicated commercial landing for the city;
2. a regional price guide;
3. the national price guide;
4. a foundational planning guide.

Examples:

    Lisboa -> Cascais          same_cluster
    Lisboa -> Lisboa-Porto     next_step
    Lisboa -> price guide      authority
    Lisboa -> @request         conversion

    Porto -> Braga             same_cluster
    Porto -> Lisboa-Porto      next_step
    Porto -> Porto price guide authority
    Porto -> @request          conversion

### Object selection algorithm

For an object source, choose:

1. a related object with similar handling requirements;
2. the next preparation, measurement, packing, or safety step;
3. a dedicated object-service landing when available, otherwise an authority
   guide;
4. `@request`.

Examples:

    refrigerator -> washing machine     same_cluster
    refrigerator -> prepare refrigerator prerequisite
    refrigerator -> refrigerator service commercial
    refrigerator -> @request            conversion

### Packing selection algorithm

For a packing source, choose:

1. another packing article covering a related material or risk;
2. the natural next packing or transport step;
3. a relevant object, planning, or safety authority article;
4. `@request`.

### Planning selection algorithm

For a planning source, choose:

1. the closest article in the same planning stage;
2. the next chronological or decision-making step;
3. a relevant price, packing, object, or safety authority article;
4. `@request`.

### Price selection algorithm

For a price source, choose:

1. another price article with the closest scope;
2. the next price-comparison or cost-reduction step;
3. a directly relevant city or service landing when available, otherwise a
   planning authority article;
4. `@request`.

### Rights selection algorithm

For a rights source, choose:

1. another rights or safety article addressing the closest risk;
2. the next verification or prevention step;
3. a relevant planning, packing, or object authority article;
4. `@request`.

### Incoming topology for new batches

Every new article must receive at least two incoming article relationships.

For a homogeneous batch without sufficient existing incoming links, create two
independent deterministic topologies:

1. one `same_cluster` ring;
2. one journey ring.

For ordered batch nodes `A, B, C, D, E`, an acceptable topology is:

    same_cluster:
    A -> B
    B -> C
    C -> D
    D -> E
    E -> A

    journey:
    A -> C
    C -> E
    E -> B
    B -> D
    D -> A

The journey ring must not duplicate the `same_cluster` destination for any
source.

Existing incoming links may replace ring edges only when every new article
still receives at least two incoming article links.

### Batch planning algorithm

For each new batch:

1. load the registry and existing article corpus;
2. identify new topic ids and their clusters;
3. preserve explicit registry relations where they satisfy this standard;
4. select `same_cluster` targets deterministically;
5. select independent journey targets deterministically;
6. select `authority` or `commercial` targets;
7. append the required `@request` conversion;
8. reject self-links, duplicate targets, duplicate reasons, and priority gaps;
9. calculate incoming and outgoing article-link counts for the future corpus;
10. adjust only the minimum number of existing relationships needed to satisfy
    graph gates;
11. validate the canonical map before rendering article JSON;
12. run the corpus release audit before publication.

### Acceptance criteria for a generated batch

A generated batch is valid only when:

- every source has exactly four relationship objects;
- priorities are exactly `1`, `2`, `3`, and `4`;
- every source has one `same_cluster` relationship;
- every source has one journey relationship;
- every source has one `authority` or `commercial` relationship;
- every source has one `conversion` relationship targeting `@request`;
- no source targets itself;
- targets and reasons are unique within each source;
- every structured article has at least two incoming article links;
- every structured article has at least two outgoing article links;
- broken links, orphan articles, and dead ends remain zero;
- rendered `related_links` exactly match the canonical map.

## Graph quality gates

A release-ready corpus must have:

- zero broken internal links;
- zero self-links;
- zero duplicate outgoing links;
- zero orphan structured articles;
- zero dead-end structured articles;
- at least two incoming article links per structured article;
- at least two outgoing article links per structured article.

Concentration and cluster-balance metrics remain analytical signals,
not automatic release blockers.

## Maintenance workflow

For each new article:

1. insert it into its cluster ring;
2. add at least two outgoing article links;
3. add incoming links from at least two existing articles;
4. preserve exactly four `related_links`;
5. run `scripts/corpus_release_audit.py`;
6. verify all graph quality gates;
7. inspect the cluster matrix before commit.

## Current corpus model

The initial 37-article corpus uses manually reviewed link rings:

- regional city rings;
- one planning ring;
- one packing ring;
- one objects ring;
- one prices ring;
- one fully connected rights cluster.

Cross-cluster links follow the user journey:

`Cities → Prices → Planning → Packing → Objects → Rights`

The request form remains the main conversion endpoint but does not
replace topical article-to-article links.
