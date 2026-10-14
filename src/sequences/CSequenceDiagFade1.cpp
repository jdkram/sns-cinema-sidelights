// human-contributors: Jonny Kram
#include "CSequenceDiagFade1.h"

#include <iostream>
using namespace std;

// LED 12 is the last channel on board 0x40 — a useful boundary-case choice.
// No loop: run for ~12 seconds then stop.
CSequenceDiagFade1::CSequenceDiagFade1(CLEDManager *pLEDManager) :
        CSequence(pLEDManager, false) {

    cout << "[DiagFade1] Single FadeEvent on LED 12. Watch LED 12 only." << endl;
    cout << "[DiagFade1] Should fade up over 5s, then down over 5s." << endl;
    cout << "[DiagFade1] If nothing happens, FadeEvent is broken in the engine." << endl;

    brightnessSetEventAddAllLeds(0, 0.0f);      // clear all LEDs at start

    fadeEventAdd(12, 100, 1.0f, 5.0f);          // fade LED 12: 0 -> 100 over 5s
    fadeEventAdd(12,   0, 7.0f, 5.0f);          // fade LED 12: 100 -> 0 over 5s

    mSequenceLengthSeconds = 13.0f;
}
