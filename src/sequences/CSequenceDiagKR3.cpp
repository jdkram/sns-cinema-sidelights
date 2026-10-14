// human-contributors: Jonny Kram
#include "CSequenceDiagKR3.h"

#include <iostream>
using namespace std;

// STAGGER < FADE_TIME means overlap: LED 2 starts fading up while LED 1 is
// still fading down. That temporal overlap is exactly what KnightRider relies
// on, and is the untested path if DiagFadeSeq (no overlap) passes but
// KnightRider fails.
CSequenceDiagKR3::CSequenceDiagKR3(CLEDManager *pLEDManager) :
        CSequence(pLEDManager, true) {

    cout << "[DiagKR3] 3-LED overlapping sweep on LEDs 1-2-3. Loops." << endl;
    cout << "[DiagKR3] Should see a bright spot moving 1->2->3->2->1 continuously." << endl;
    cout << "[DiagKR3] If nothing: FadeEvent overlap is broken. Compare to DiagFadeSeq." << endl;

    brightnessSetEventAddAllLeds(0, 0.0f);

    const float STAGGER   = 1.5f;
    const float FADE_TIME = 2.5f;

    float t = 0.01f;

    // Forward: 1 -> 2 -> 3
    for (int led = 1; led <= 3; led++) {
        fadeEventAdd(led, 100, t,             FADE_TIME);
        fadeEventAdd(led,   0, t + FADE_TIME, FADE_TIME);
        t += STAGGER;
    }

    // Backward: 2 -> 1  (LED 3 already covered above)
    for (int led = 2; led >= 1; led--) {
        fadeEventAdd(led, 100, t,             FADE_TIME);
        fadeEventAdd(led,   0, t + FADE_TIME, FADE_TIME);
        t += STAGGER;
    }

    mSequenceLengthSeconds = t;
    cout << "[DiagKR3] Loop length: " << mSequenceLengthSeconds << "s" << endl;
}
