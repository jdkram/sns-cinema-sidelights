#ifndef CSEQUENCEDIAGFADE1_H
#define CSEQUENCEDIAGFADE1_H
// human-contributors: Jonny Kram

#include "CSequence.h"
#include "../CLEDManager.h"

// Engine diagnostic: one FadeEvent on one LED (LED 12).
// Fades 0->100 over 5s, then 100->0 over 5s. Runs once, no loop.
//
// Purpose: if the DIAG sweep (direct write) lights LED 12 but this sequence
// does not, the FadeEvent mechanism in the sequence engine is broken.
// If this works, FadeEvent is fundamentally functional.
class CSequenceDiagFade1 : public CSequence {

public:
    CSequenceDiagFade1(CLEDManager* pLEDManager);
};

#endif
