// human-contributors: Jonny Kram
#include "CSequenceDiagFadeSeq.h"

#include <iostream>
using namespace std;

// One representative LED from each of the four physical groups (two boards,
// two wiring halves each): LED 1 (0x40 first half), LED 7 (0x40 second half),
// LED 13 (0x60 first half), LED 19 (0x60 second half).
// No overlap: each LED has fully finished before the next one starts.
CSequenceDiagFadeSeq::CSequenceDiagFadeSeq(CLEDManager *pLEDManager) :
        CSequence(pLEDManager, false) {

    cout << "[DiagFadeSeq] Sequential FadeEvents on LEDs 1, 7, 13, 19 (one at a time)." << endl;
    cout << "[DiagFadeSeq] Each LED fades up then down over 4s. 5s gap between each." << endl;
    cout << "[DiagFadeSeq] Total: ~28s. No overlap between LEDs." << endl;

    brightnessSetEventAddAllLeds(0, 0.0f);

    const float FADE_UP   = 2.0f;
    const float FADE_DOWN = 2.0f;
    const float GAP       = 5.0f;   // silence between LEDs -- makes each step obvious
    const int   LEDS[]    = {1, 7, 13, 19};

    float t = 1.0f;
    for (int i = 0; i < 4; i++) {
        int led = LEDS[i];
        fadeEventAdd(led, 100, t,             FADE_UP);
        fadeEventAdd(led,   0, t + FADE_UP,   FADE_DOWN);
        t += FADE_UP + FADE_DOWN + GAP;
    }

    mSequenceLengthSeconds = t;
}
