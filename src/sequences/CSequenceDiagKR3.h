#ifndef CSEQUENCEDIAGKR3_H
#define CSEQUENCEDIAGKR3_H
// human-contributors: Jonny Kram

#include "CSequence.h"
#include "../CLEDManager.h"

// Engine diagnostic: 3-LED KnightRider-style sweep, looping.
// LEDs 1, 2, 3 only. STAGGER=1.5s, FADE_TIME=2.5s — slow enough to observe,
// but with deliberate temporal overlap (each new LED starts before the
// previous one has finished fading down).
//
// Purpose: tests the exact pattern type that KnightRider uses — staggered
// start times with overlap across different LEDs — but at minimal scale.
// If DiagFadeSeq works but this does not, the bug is in overlapping events.
// If this works, scale up to full KnightRider.
class CSequenceDiagKR3 : public CSequence {

public:
    CSequenceDiagKR3(CLEDManager* pLEDManager);
};

#endif
