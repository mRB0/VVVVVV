#ifndef SWNHOOK_H__
#define SWNHOOK_H__

#include <Python.h>
#include <vector>

class Game;
class entityclass;

enum Direction {
    DirectionLeft,
    DirectionRight
};

enum PressedDirection {
	PressedDirectionNone,
	PressedDirectionLeft,
	PressedDirectionRight
};

struct Enemy {
    Direction direction;
    int xp;
    int yp;
};

struct GravitronState {
    bool inGame;
    bool alive;
    std::vector<Enemy> activeEnemies;
    int playerXp;
    int playerYp;
    float playerVx;
    float playerVy;
};


class SWNHook {
public:
	SWNHook(Game &game, entityclass &obj);
	~SWNHook();

	void processFrame();
	PressedDirection getLastPressedDirection();
	bool pressLeft();
	bool pressRight();

    long getGenerationNumber() {
        return generationNumber;
    }

    long getGenomeNumber() {
        return genomeNumber;
    }

    double getCurrentGenerationBestFitness() {
        return currentGenerationBestFitness;
    }
    
    double getPreviousGenerationBestFitness() {
        return previousGenerationBestFitness;
    }
    
private:
	void updateState();
	PressedDirection consultPython();

	Game &game;
	entityclass &obj;
	PyObject *pModule;
	PyObject *pFuncRun;

	GravitronState state;
	PressedDirection lastPressedDirection = PressedDirectionNone;

    long generationNumber = -1;
    double currentGenerationBestFitness = 0;
    double previousGenerationBestFitness = 0;
    long genomeNumber = -1;
};

#endif
