---
lab4_comms:
  awareness: 2026-10-12T06:40:09Z          # NIS2: the on-call acknowledged the P1 ticket, knowing orders were failing
  detection: 2026-10-12T06:39:19Z          # KSC: ShopCheckoutErrors fired (the detection of the postmortem)
  classification: 2026-10-12T07:30:00Z     # DORA: classified as major after the impact review
  nis2:
    early_warning_due: 2026-10-13T06:40:09Z      # awareness + 24 h
    notification_due: 2026-10-15T06:40:09Z       # awareness + 72 h
    notification_sent: 2026-10-13T09:00:00Z
    final_report_due: 2026-11-13T09:00:00Z       # one calendar month after notification_sent
  ksc:
    early_warning_due: 2026-10-13T06:39:19Z      # detection + 24 h
    notification_due: 2026-10-15T06:39:19Z       # detection + 72 h
    notification_sent: 2026-10-13T09:00:00Z
    final_report_due: 2026-11-13T09:00:00Z       # one calendar month after notification_sent
  dora:
    initial_due: 2026-10-12T11:30:00Z            # classification + 4 h, earlier than awareness + 24 h
    initial_sent: 2026-10-12T10:00:00Z
    intermediate_due: 2026-10-15T10:00:00Z       # initial_sent + 72 h
    intermediate_sent: 2026-10-14T10:00:00Z
    final_due: 2026-11-14T10:00:00Z              # one calendar month after intermediate_sent
  log:
    - {at: 2026-10-12T10:00:00Z, to: the financial supervisor (KNF), what: DORA initial notification of a major ICT-related incident}
    - {at: 2026-10-12T12:00:00Z, to: the CSIRT (CSIRT NASK), what: NIS2 and KSC early warning}
    - {at: 2026-10-13T09:00:00Z, to: the CSIRT (CSIRT NASK), what: NIS2 and KSC incident notification}
    - {at: 2026-10-14T10:00:00Z, to: the financial supervisor (KNF), what: DORA intermediate report}
    - {at: 2026-11-10T10:00:00Z, to: the CSIRT (CSIRT NASK), what: NIS2 and KSC final report}
    - {at: 2026-11-12T10:00:00Z, to: the financial supervisor (KNF), what: DORA final report}
---
<!-- ai-generated: 60% - Claude Code (Opus 5.5) computed the deadlines with a script from INCIDENT-SPEC.md I-30 and drafted the text; the author chose and defends the three instants -->

# Communications log: the regulators' clocks

The incident of `postmortem.md` (recording lab4-rec-4, Monday 12 October 2026), treated as if the shop were an
entity under NIS2, the Polish KSC act and DORA at once, and the incident significant under the first two and major
under the third. Every instant is UTC. On 12 October Warsaw is on summer time (UTC+2), so 06:39:19Z is 08:39:19 on a
Warsaw clock; the final reports fall after Warsaw goes back to UTC+1 on 25 October, so 2026-11-13T09:00:00Z is
10:00, not 11:00, in Warsaw. Writing UTC keeps that out of the arithmetic.

## The three instants you defend

**Detection (KSC), 06:39:19Z.** The amended KSC act counts "od momentu jego wykrycia", from the moment the incident
was detected. The earliest moment our own systems detected it is the moment the P1 alert ShopCheckoutErrors began
firing on checkout's error ratio: the same instant as the detection of the postmortem, recomputed by the checker from
the snapshot. Nobody had looked at it yet, but the act does not wait for a person: the monitoring is ours, and its
detection is our detection. Choosing the later acknowledgement would buy 50 seconds and lose the argument.

**Awareness (NIS2), 06:40:09Z.** NIS2 counts from "becoming aware of the significant incident". At 06:40:09Z the
on-call acknowledged the P1 ticket after reading the page, which said that more than a threshold share of checkout's
orders failed. From that moment a person responsible for the service knew that buyers could not pay, which is what
makes the incident significant for a shop. The extent (8 of 53 orders, three faults) came later, but awareness does
not require the full picture, and we do not want to argue that an engineer who acknowledged a P1 on failing orders
was not aware of it.

**Classification (DORA), 07:30:00Z.** DORA's initial notification runs from the classification of the incident as
major, which needs the criteria of the classification standard: clients affected, duration, critical services hit.
By 07:30Z, 46 minutes after recovery, the impact review had the numbers (orders failed for about eight minutes, the
payment path of every client affected, a critical service). The classification is within 24 hours of awareness, so
the initial notification is due at the earlier of classification + 4 h (11:30Z) and awareness + 24 h (06:40:09Z on
13 October): 11:30Z on 12 October.

## The log

| at (UTC) | to | what | which clock |
|---|---|---|---|
| 2026-10-12T10:00:00Z | the financial supervisor (KNF) | DORA initial notification | due 11:30Z, sent 90 minutes early |
| 2026-10-12T12:00:00Z | the CSIRT (CSIRT NASK) | NIS2 and KSC early warning | due 2026-10-13T06:39:19Z (KSC, the earlier of the two) |
| 2026-10-13T09:00:00Z | the CSIRT | NIS2 and KSC incident notification | due 2026-10-15T06:39:19Z (KSC) and 06:40:09Z (NIS2) |
| 2026-10-14T10:00:00Z | the financial supervisor | DORA intermediate report | due 72 h after the initial notification, 2026-10-15T10:00:00Z |
| 2026-11-10T10:00:00Z | the CSIRT | NIS2 and KSC final report | due one month after the notification, 2026-11-13T09:00:00Z |
| 2026-11-12T10:00:00Z | the financial supervisor | DORA final report | due one month after the intermediate report, 2026-11-14T10:00:00Z |

The NIS2 and KSC reports go out together, to the same CSIRT, so each one is sent before the earlier of its two
deadlines; the KSC one is always the earlier by 50 seconds, because detection came before awareness. The final
reports go out a few days before their deadlines because the postmortem's action items (ITSM-41 to ITSM-46) will
not be finished by then, and a final report that says so on time is better than a late complete one.
