## Purpose

Turns a property listing into every lot it sells, each matched to a group of HM Land Registry INSPIRE titles close to its stated acreage, confirmed by the user, using the cheapest evidence first.

## ADDED Requirements

### Requirement: Structured page data is read before any model
When a listing page is fetched, the system SHALL capture its JSON-LD blocks, embedded app state and map meta tags before scripts are stripped, and SHALL read from them, without a model call, the point, total area, address, the listing's own description, lot notes, image URLs and any boundary polygon. A reader for the page's portal SHALL be used when one exists (Savills, Rightmove, Zoopla, Knight Frank, OnTheMarket), and a generic JSON-LD reader otherwise. A reader that finds none of its fields SHALL return nothing rather than fail.

#### Scenario: Portal app state
- **WHEN** a Savills page embeds its property in `__NEXT_DATA__` with coordinates, acreage and a description
- **THEN** the listing facts have that point, the acreage and the description, and no model is called for them

#### Scenario: Unknown portal with JSON-LD
- **WHEN** a page from an unlisted agent has a schema.org block with `geo` and `address`
- **THEN** the JSON-LD reader gives the point and address

#### Scenario: Portal changed its layout
- **WHEN** the portal reader finds none of its field paths
- **THEN** the reader returns nothing and the next tier runs, without an error

### Requirement: Lots come from one small model call on the listing's own text
When the structured data does not state the lots, the system SHALL make at most one model call per listing, with structured output, on the listing's own description and notes (or, without them, on the listing part of the page text), capped at 6,000 characters. The output SHALL list the lots (name, acres, what3words, postcode, address), the total acres and the tenure. The call SHALL be skipped when the structured data already gives the lots, or gives a point and the description does not mention lots.

#### Scenario: Farm sold in two lots
- **WHEN** the description says a 200-acre farm is offered as a whole or in two lots of 194 and 6 acres, with a what3words for each lot in the notes
- **THEN** the output has two lots with those acreages and what3words, and a total of 200 acres

#### Scenario: Single house with a point
- **WHEN** the structured data gives a point and the description does not mention lots
- **THEN** no model is called and the listing has one lot anchored at that point

#### Scenario: Boilerplate before the listing
- **WHEN** the page text starts with 10,000 characters of cookie banners and menus
- **THEN** none of that text is sent to the model

### Requirement: Each lot is anchored by its best evidence
The system SHALL anchor each lot at a portal polygon, else its what3words (converted with the what3words API when a key is set), else the listing point, else its postcode. The listing point SHALL anchor the lot whose acreage best matches the group grown from it. A lot with no anchor SHALL be shown as not placed.

#### Scenario: No what3words key
- **WHEN** the lots have what3words but no what3words key is set
- **THEN** the listing point anchors the lot whose acreage it matches best, and the other lot is shown as not placed with its what3words as text

#### Scenario: what3words key set
- **WHEN** a what3words key is set and each lot has a what3words
- **THEN** each lot is anchored at its own converted position

### Requirement: Titles are grouped by acreage
For each anchored lot, the system SHALL start with the INSPIRE title containing the anchor and add adjacent titles until the group's area matches the lot's stated acreage within ±10% or ±2 acres, whichever is larger, without a model call. Each lot SHALL be its own group; a title SHALL belong to at most one group. Each group SHALL carry an area-match score. A lot without a stated acreage SHALL get the containing title only.

#### Scenario: Acreage matched
- **WHEN** a lot of 194 acres is anchored in a field and its neighbours add up to 191 acres
- **THEN** the group holds those titles, its area is 191 acres and its score is about 0.98

#### Scenario: No acreage stated
- **WHEN** a single-property listing states no area
- **THEN** the group is the one title containing the point, as before this change

#### Scenario: Neighbouring lots
- **WHEN** two lots are anchored next to each other
- **THEN** no title appears in both groups

### Requirement: The user confirms the titles on the map
The confirmation step SHALL show every candidate title, the chosen titles per lot, and each lot's stated and matched acreage. The user SHALL be able to add or remove a title by clicking it. The confirmed set SHALL be the site boundary for the rest of the run, and SHALL be recorded in an artifact.

#### Scenario: User removes a neighbour's field
- **WHEN** the user clicks a chosen title that belongs to a neighbour and confirms
- **THEN** the run continues with the remaining titles, and later figures are measured against their union

#### Scenario: Unknown title id
- **WHEN** a decision names a title that was not a candidate
- **THEN** the decision is rejected with a clear message

#### Scenario: Confirm without edits
- **WHEN** the user confirms without clicking any title
- **THEN** the proposed groups are the site

### Requirement: The plan image is checked only on low confidence
When any placed lot's score is below 0.8, or a lot with a stated acreage has no anchor, the system SHALL look for the sale plan among the listing's gallery images, excluding floor plans, choosing it first from captions, file names and image statistics and only then with at most one low-resolution classification call. It SHALL then make at most one vision call comparing the plan with the candidate titles drawn on a map, and update the groups it matches. Results SHALL be cached per image URL and candidate set. Otherwise no image is downloaded and no vision call is made.

#### Scenario: Good area match
- **WHEN** every placed lot scores 0.8 or more
- **THEN** no image is downloaded and no vision call is made

#### Scenario: Poor area match
- **WHEN** a lot scores 0.5 and one gallery image is captioned "Sale plan"
- **THEN** that image is chosen without a classification call, one vision call compares it with the candidates, and the lot's group is marked as matched from the plan

#### Scenario: Same listing again
- **WHEN** the same listing is run again with the same candidates
- **THEN** the cached plan result is used and no model is called

### Requirement: Model use is small and recorded
A typical listing SHALL use no more than about 2k model tokens, and none when the structured data suffices. The plan check SHALL use at most one classification call and one vision call per listing. Every model call SHALL produce an artifact that records the model used; deterministic steps SHALL record their source.

#### Scenario: Artifacts per step
- **WHEN** a two-lot listing runs through lots extraction and title grouping
- **THEN** there is an artifact for the lots naming the model, and one per lot group naming the title data source and the score

### Requirement: Single-property links behave as before
A link to a single-property listing SHALL resolve to the same postcode and point as before this change, and a postcode given with the link SHALL still win without a fetch.

#### Scenario: House listing
- **WHEN** a cached single-house page that resolved to a postcode before is run again
- **THEN** it resolves to the same postcode and point

### Requirement: Tried listings stay out of git
Pages, postcodes and what3words fetched during runs SHALL be cached in a gitignored directory. Committed fixture folders SHALL hold only curated pages added on purpose. Lookups SHALL read committed fixtures first, then the live cache, then the network.

#### Scenario: Trying a new listing
- **WHEN** a user runs a listing link that is not a curated fixture
- **THEN** its page and postcode are cached under the gitignored directory, and `git status` shows no new files

#### Scenario: Curated demo page
- **WHEN** a curated page exists in the committed fixtures
- **THEN** it is used and nothing is fetched
