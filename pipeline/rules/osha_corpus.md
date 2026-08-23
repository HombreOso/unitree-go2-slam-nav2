# OSHA 29 CFR Part 1926 — Construction Safety Knowledge Base

Retrieval corpus for layer **B2 (Regulation Extraction)**.

> **Status of this text.** Each entry is a condensed, plain-language paraphrase
> of the cited provision, written for semantic retrieval — it is **not**
> verbatim regulatory text and has no legal force. The citation on every chunk
> is the authoritative source; verify against eCFR Title 29 Part 1926 before
> relying on any of it for an actual inspection. Grounding the model in these
> chunks is what makes its findings traceable (paper, Section 3.4), and the
> citation is the thing that gets traced.

Chunks are delimited by `## [ID] citation — title`. The retriever in
`pipeline/rag.py` splits on those headings, so keep the format.

---

## [FALL-001] 1926.501(b)(1) — Unprotected sides and edges

Each employee on a walking/working surface with an unprotected side or edge
**6 feet (1.8 m) or more** above a lower level must be protected by a guardrail
system, a safety net system, or a personal fall arrest system. Working on top of
machinery, equipment decks or platforms at that height without one of those
three systems is a violation. Keywords: unprotected edge, working at height,
standing on machine, no guardrail, no harness, fall arrest, elevated platform.

## [FALL-002] 1926.501(b)(4) — Holes and floor openings

Employees working above or near a hole (including skylights) must be protected
from falling through it by covers, guardrails, or personal fall arrest. Covers
must be secured and marked. Keywords: floor opening, uncovered hole, unguarded
opening, trip and fall through.

## [FALL-003] 1926.502(d) — Personal fall arrest systems

Where fall arrest is the chosen protection, the worker must actually be wearing
a full body harness connected to an anchorage capable of supporting the load.
A harness that is present but not worn or not connected provides no protection.
Keywords: harness not worn, unattached lanyard, no anchorage, no tie-off.

## [LADDER-001] 1926.1053(b)(1) — Ladder side-rail extension

A portable ladder used to access an upper landing surface must have its side
rails extend **at least 3 feet (0.9 m)** above that landing. If it cannot, the
ladder must be secured at the top and a grasping device provided. Keywords:
ladder too short, rails do not extend, no handhold at top.

## [LADDER-002] 1926.1053(b)(6) and (b)(8) — Ladder placement and stability

Portable ladders must be used only on stable and level surfaces unless secured
to prevent accidental displacement, and must not be used on slippery surfaces or
placed on boxes, barrels, machinery or other unstable bases to gain height. A
ladder leaned against a machine, a forklift, or anything that can move or be
moved is a violation. Where a ladder can be displaced by traffic or equipment
activity, it must be secured or the area barricaded. Keywords: ladder against
machine, unsecured ladder, unstable base, ladder in traffic path, ladder can be
knocked over, not tied off.

## [LADDER-003] 1926.1053(b)(5)(i) — Ladder angle (the 4:1 rule)

A non-self-supporting portable ladder must be set at an angle where the
horizontal distance from the top support to the foot is about **one quarter** of
the working length (roughly 75 degrees from horizontal). Too shallow invites the
base to slide out; too steep invites tipping backward. Keywords: ladder angle,
4 to 1 ratio, ladder too steep, ladder too shallow, base slid out.

## [LADDER-004] 1926.1053(b)(22) and 1926.1060 — Climbing practice

Employees must face the ladder when climbing and maintain three points of
contact, and must not carry loads that could cause loss of balance. Employers
must train each employee in ladder hazards and correct use. Keywords: three
points of contact, facing the ladder, carrying material while climbing.

## [ACCESS-001] 1926.1051(a) — Means of access to working levels

A stairway or ladder must be provided at every personnel point of access where
there is a break in elevation of **19 inches (48 cm) or more** and no ramp,
runway, embankment or personnel hoist is provided. Climbing on stacked material,
crates, buckets or equipment instead of an approved stairway or ladder is a
violation. Keywords: no ladder provided, climbing on crates, improvised step,
makeshift access, stacked boxes used as steps.

## [PPE-001] 1926.100(a) — Head protection

Employees working in areas where there is a possible danger of head injury from
impact, falling or flying objects, or electrical shock and burns must be
protected by protective helmets. A hard hat lying on the ground, hanging on
equipment, or otherwise not on the worker's head does not satisfy this.
Working on or under a ladder, near a raised load, or beneath overhead work
without a hard hat is a violation. Keywords: no hard hat, no helmet, head
protection missing, hard hat on floor, bare head under overhead load.

## [PPE-002] 1926.95(a) — Personal protective equipment generally

PPE appropriate to the hazard must be provided, used, and maintained wherever
hazards capable of causing injury are encountered. Providing PPE is not enough —
it must actually be worn. Keywords: PPE not worn, PPE on the ground, protective
equipment available but unused.

## [PPE-003] 1926.201 / high-visibility apparel — Warning garments

Workers exposed to vehicular or equipment traffic must wear warning vests or
other high-visibility garments so they are conspicuous to operators. Where site
policy or signage requires high-visibility apparel beyond a marked point,
entering without it is a violation of that policy. Working near an operating
forklift or other mobile equipment without a hi-vis vest is a hazard.
Keywords: no vest, no high visibility clothing, hi-vis required sign, worker not
conspicuous, near moving equipment.

## [PPE-004] 1926.102(a) — Eye and face protection

Eye and face protection must be provided and used when machines or operations
present potential eye or face injury from physical, chemical, or radiation
agents. Keywords: no safety glasses, no goggles, no face shield.

## [HOUSE-001] 1926.25(a) — Housekeeping, debris clearance

During the course of construction, form and scrap lumber, protruding nails,
and **all other debris must be kept cleared** from work areas, passageways and
stairs, in and around buildings and structures. Bricks, offcuts, tools and
rubble scattered across a walkway is a violation and a trip hazard. Keywords:
debris in walkway, scattered bricks, rubble on floor, clutter, poor
housekeeping, trip hazard, obstructed passage.

## [HOUSE-002] 1926.25(c) — Waste containers and disposal

Containers must be provided for the collection and separation of waste and
debris, and waste must be disposed of at frequent and regular intervals.
Keywords: no waste container, debris piling up, rubbish not removed.

## [MAT-001] 1926.250(a)(1) — Storage of materials, stability

All materials stored in tiers must be stacked, racked, blocked, interlocked or
otherwise secured to prevent sliding, falling or collapse. Bricks or other
material left loose on an elevated platform, near a worker's feet, or at the
edge of a raised surface can slide or fall and is a violation. Keywords:
unsecured stack, material on platform edge, bricks near feet at height, load
could slide or fall, unstable tier.

## [MAT-002] 1926.250(b)(1) — Aisles and passageways kept clear

Aisles and passageways must be kept clear to provide for the free and safe
movement of material handling equipment and employees. Material stacked in the
middle of a walkway obstructs egress and is a violation. Keywords: aisle
blocked, walkway obstructed, stack in the middle of the path, cannot pass.

## [MAT-003] 1926.602(c)(1) and 1926.600(a)(3) — Material handling equipment

Powered industrial truck (forklift) operations must comply with the applicable
requirements: loads must be stable and safely arranged, and equipment left
unattended must have its load fully **lowered**, controls neutralised, power
shut off and brakes set. Bricks or other material left on raised forks with no
operator present is a violation — anyone walking beneath is exposed to a
struck-by hazard. Keywords: forklift unattended, load raised, forks elevated,
load on forks, material stored on forks, struck-by, nobody operating.

## [HOIST-001] 1926.552(b)(1) — Material hoists: no riders

Material hoists, material lifts and lift tables are rated for material, not for
people. Employees must **not** ride on material hoists, and a sign reading "NO
RIDERS PERMITTED" must be posted. Using a material lift table, pallet lift or
similar to raise a person is a violation, and typically also creates an
unprotected fall exposure. Keywords: person on material lift, riding a hoist,
lift table used to elevate worker, not rated for personnel, no riders.

## [HOIST-002] 1926.451(a) and 1926.451(g) — Scaffolds and platforms

Scaffolds must be capable of supporting their own weight plus four times the
maximum intended load, and employees on a scaffold more than 10 feet above a
lower level must be protected by guardrails or a fall arrest system. Improvised
platforms are not scaffolds. Keywords: improvised platform, no guardrail on
platform, overloaded scaffold, working on unrated platform.

## [ELEC-001] 1926.404(b)(1) — Ground-fault protection

The employer must use either ground-fault circuit interrupters (**GFCI**) on all
125-volt, single-phase, 15/20/30-ampere receptacle outlets not part of the
permanent wiring, **or** an assured equipment grounding conductor program, for
receptacles used by employees. Temporary power and extension cords in damp or
wet locations without GFCI protection is a violation. Keywords: no GFCI, wet
area, damp location, temporary power, extension cord in water, puddle, no
ground fault protection.

## [ELEC-002] 1926.405(a)(2)(ii) — Temporary wiring and flexible cords

Temporary electrical wiring and flexible cords must be protected from accidental
damage; cords must not be run through puddles, across walkways where they will
be driven over or walked on, or through doorways and windows where they can be
pinched, without protection. Sharp corners and projections must be avoided.
Keywords: cord through water, cord across walkway, cord subject to damage, cord
pinched, unprotected flexible cord.

## [ELEC-003] 1926.405(j)(1)(i) — Portable cord condition and use

Flexible cords and cables must be in continuous lengths without splice or tap,
free of damage to the outer jacket, and used only in the ways permitted.
Damaged, spliced or improperly used cords must be removed from service.
Keywords: damaged cord, frayed cable, spliced cord, cut insulation.

## [ELEC-004] 1926.416(a)(1) — Work near energised parts

No employee may work near any part of an electric power circuit that they could
contact in the course of work unless the employee is protected against electric
shock by de-energising and grounding the circuit, or by guarding it with
effective insulation. Keywords: exposed conductor, energised circuit, no
lockout, contact with live parts.

## [ELEC-005] 1926.404(b)(1)(iii) — Assured equipment grounding conductor program

Where the assured equipment grounding conductor program is used instead of
GFCIs, it must be written, enforced, and include specified inspections and tests
of cord sets and receptacles, with records available. Absent that documented
program, GFCI protection is required. Keywords: grounding conductor program, no
inspection records, untested cord set.

## [SIGN-001] 1926.200(a) and (c) — Signs and barricades

Signs and symbols required by this subpart must be visible at all times where a
hazard exists and removed or covered promptly when the hazard is gone. Caution
signs must be used only to warn against potential hazards or to caution against
unsafe practices. Where signage requires specific PPE beyond a point, that
requirement applies to everyone past the sign. Keywords: caution sign, danger
sign, warning signage, PPE required beyond this point, sign posted.

## [STRUCK-001] 1926.600(a)(6) — Equipment left unattended at night / near traffic

Equipment left unattended at night adjacent to a highway or construction area in
normal use must have appropriate lights, reflectors or barricades to identify
its location. Keywords: unattended equipment, no barricade, unlit machine.

## [GEN-001] 1926.20(b)(2) — Frequent and regular inspections

The employer must initiate and maintain accident-prevention programs including
frequent and regular inspections of the job site, materials and equipment, by
competent persons. This is the regulatory basis for routine safety inspection
itself. Keywords: inspection program, competent person, regular jobsite
inspection.

## [GEN-002] 1926.21(b)(2) — Hazard recognition training

The employer must instruct each employee in the recognition and avoidance of
unsafe conditions and the regulations applicable to the work environment, to
control or eliminate hazards. Keywords: training, hazard recognition, employee
instruction.
