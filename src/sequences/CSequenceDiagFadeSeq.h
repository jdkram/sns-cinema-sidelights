#ifndef CSEQUENCEDIAGFADESEQ_H
#define CSEQUENCEDIAGFADESEQ_H
// human-contributors: Jonny Kram

#include "CSequence.h"
#include "../CLEDManager.h"

// Engine diagnostic: four LEDs firing in sequence, no temporal overlap.
// LEDs 1, 7, 13, 19 each fade 0->100->0 over 4s, one at a time, 5s apart.
//
// Purpose: if DiagFade1 works but this does not, the problem is specifically
// with staggered start times on different LEDs — the core of KnightRider.
// If this works, temporal staggering is fine and the KnightRider bug is
// likely in the overlapping-events or channel-reservation logic.
class CSequenceDiagFadeSeq : public CSequence {

public:
    CSequenceDiagFadeSeq(CLEDManager* pLEDManager);
};

#endif
