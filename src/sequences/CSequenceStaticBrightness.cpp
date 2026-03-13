// human-contributors: Jonny Kram
#include "CSequenceStaticBrightness.h"

CSequenceStaticBrightness::CSequenceStaticBrightness(CLEDManager *pLEDManager, int pBrightness) :
        CSequence(pLEDManager) {

    brightnessSetEventAddAllLeds(pBrightness, 0.0f);
}
