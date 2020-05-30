#include "SWNHook.h"
#include "Game.h"
#include "Entity.h"
#include "Ent.h"

#include <Python.h>

#include <vector>
#include <string>
#include <exception>

static std::wstring moduleRoot(L"../src");
static std::string entryPointModuleName("swnhook");
static std::string runFunctionName("run");

static PyObject *createDictForGravitronState(GravitronState const &state) {
    PyObject *dict = PyDict_New();

    {  
        PyObject *inGame = PyBool_FromLong(state.inGame);
        PyDict_SetItemString(dict, "inGame", inGame);
        Py_DECREF(inGame);
    }
    
    {
        PyObject *alive = PyBool_FromLong(state.alive);
        PyDict_SetItemString(dict, "alive", alive);
        Py_DECREF(alive);
    }

    {
        PyObject *playerXp = PyLong_FromLong(state.playerXPosition);
        PyDict_SetItemString(dict, "playerXPosition", playerXp);
        Py_DECREF(playerXp);
    }

    {
        PyObject *playerYp = PyLong_FromLong(state.playerYPosition);
        PyDict_SetItemString(dict, "playerYPosition", playerYp);
        Py_DECREF(playerYp);
    }

    {
        PyObject *playerVx = PyFloat_FromDouble(state.playerXVelocity);
        PyDict_SetItemString(dict, "playerXVelocity", playerVx);
        Py_DECREF(playerVx);
    }

    {
        PyObject *playerVy = PyFloat_FromDouble(state.playerYVelocity);
        PyDict_SetItemString(dict, "playerYVelocity", playerVy);
        Py_DECREF(playerVy);
    }

    {
        PyObject *enemies = PyList_New(0);

        for (Enemy const &enemy : state.activeEnemies) {
            PyObject *enemyDict = PyDict_New();

            {
                long direction = enemy.direction == DirectionLeft ? -1 : 1;
                PyObject *enemyDirection = PyLong_FromLong(direction);
                PyDict_SetItemString(enemyDict, "direction", enemyDirection);
                Py_DECREF(enemyDirection);
            }

            {
                PyObject *enemyXp = PyLong_FromLong(enemy.xPosition);
                PyDict_SetItemString(enemyDict, "xPosition", enemyXp);
                Py_DECREF(enemyXp);
            }

            {
                PyObject *enemyYp = PyLong_FromLong(enemy.yPosition);
                PyDict_SetItemString(enemyDict, "yPosition", enemyYp);
                Py_DECREF(enemyYp);
            }

            PyList_Append(enemies, enemyDict);

            Py_DECREF(enemyDict);
        }

        PyDict_SetItemString(dict, "activeEnemies", enemies);
        Py_DECREF(enemies);
    }

    return dict;
}


SWNHook::SWNHook(Game &game, entityclass &obj) 
	: game(game), obj(obj)
{
    state = GravitronState{ false, false, std::vector<Enemy>{}, 0, 0, 0, 0 };

    {
	    std::wstring oldPath(Py_GetPath());
	    std::wstring newPath = oldPath + L":" + moduleRoot;
	    Py_SetPath(newPath.c_str());
	}


    Py_Initialize();

    {
        PyObject *pName = PyUnicode_DecodeFSDefault(entryPointModuleName.c_str());
    	pModule = PyImport_Import(pName);
        Py_DECREF(pName);
    }

    if (pModule == NULL) {
        PyErr_Print();
        char buf[1000];
        snprintf(buf, sizeof(buf), "Failed to load \"%s\"\n", entryPointModuleName.c_str());
        fprintf(stderr, "%s", buf);
		throw std::runtime_error(std::string(buf));
    }

    pFuncRun = PyObject_GetAttrString(pModule, runFunctionName.c_str());
    /* pFuncRun is a new reference */

    if (!(pFuncRun && PyCallable_Check(pFuncRun))) {
        if (PyErr_Occurred()) {
            PyErr_Print();
        }
        char buf[1000];
        snprintf(buf, sizeof(buf), "Cannot find function \"%s\"\n", runFunctionName.c_str());
        fprintf(stderr, "%s", buf);
        throw std::runtime_error(std::string(buf));
    }
}

SWNHook::~SWNHook() {
    Py_XDECREF(pFuncRun);
    Py_XDECREF(pModule);
}

void SWNHook::processFrame() {
    GravitronState oldState = state;
    updateState();

    lastPressedDirection = consultPython();
    //fprintf(stderr, "Pressed %d\n", lastPressedDirection);

}

PressedDirection SWNHook::getLastPressedDirection() {
    return lastPressedDirection;
}

PressedDirection SWNHook::consultPython() {
    PyObject *runResult;
    {
        PyObject *pArgs = PyTuple_New(1);
        PyTuple_SetItem(pArgs, 0, createDictForGravitronState(state));
        runResult = PyObject_CallObject(pFuncRun, pArgs);
        Py_DECREF(pArgs);
    }

    if (runResult == NULL) {
        PyErr_Print();
        char buf[1000];
        snprintf(buf, sizeof(buf), "Call failed\n");
        fprintf(stderr, "%s", buf);
        throw std::runtime_error(std::string(buf));
    }

    long directionNumber;

    {
        PyObject *directionObject = PyObject_GetAttrString(runResult, "pressed_direction");
        directionNumber = PyLong_AsLong(directionObject);
        Py_DECREF(directionObject);
    }

    {
        PyObject *generationStatus = PyObject_GetAttrString(runResult, "generation_status");

        {
            PyObject *currentGenerationNumber = PyObject_GetAttrString(generationStatus, "current");
            if (currentGenerationNumber == Py_None) {
                this->generationNumber = -1;
            } else {
                this->generationNumber = PyLong_AsLong(currentGenerationNumber);
            }
            Py_DECREF(currentGenerationNumber);
        }

        {
            PyObject *bestFitness = PyObject_GetAttrString(generationStatus, "previous_best_fitness");
            if (bestFitness == Py_None) {
                this->previousGenerationBestFitness = 0;
            } else {
                this->previousGenerationBestFitness = PyFloat_AsDouble(bestFitness);
            }
            Py_DECREF(bestFitness);
        }


        Py_DECREF(generationStatus);
    }

    {
        PyObject *currentGenomeNumber = PyObject_GetAttrString(runResult, "genome_number");
        if (currentGenomeNumber == Py_None) {
            this->genomeNumber = -1;
        } else {
            this->genomeNumber = PyLong_AsLong(currentGenomeNumber);
        }
        Py_DECREF(currentGenomeNumber);
    }

    {
        PyObject *currentGenerationBestFitness = PyObject_GetAttrString(runResult, "current_generation_best_fitness");
        if (currentGenerationBestFitness == Py_None) {
            this->currentGenerationBestFitness = 0;
        } else {
            this->currentGenerationBestFitness = PyFloat_AsDouble(currentGenerationBestFitness);
        }
        Py_DECREF(currentGenerationBestFitness);
    }

    {
        PyObject *directionObject = PyObject_GetAttrString(runResult, "pressed_direction");
        directionNumber = PyLong_AsLong(directionObject);
        Py_DECREF(directionObject);
    }

    Py_DECREF(runResult);

    switch(directionNumber) {
        case -1:
            return PressedDirectionLeft;
        case 1:
            return PressedDirectionRight;
        default:
            return PressedDirectionNone;
    }
}

void SWNHook::updateState() {
    state = GravitronState{ false, false, std::vector<Enemy>{}, 0, 0, 0, 0 };

    if (!game.swnmode || game.swngame != 1) {
        state.alive = false;
        state.inGame = false;
        return;
    }

    state.inGame = true;

    //fprintf(stderr, "\nSuper Gravitron is active\n");
    
    state.alive = false;
    entclass *player = nullptr;

    for (int ie = 0; ie < obj.nentity; ++ie)
    {
        if (obj.entities[ie].rule == 0)
        {
            player = &obj.entities[ie];

            //game.test = true;
            //game.teststring = "player(" + String(int(obj.entities[i])) + "," + String(int(obj.entities[i].yp)) + ")"
            //  + ", mouse(" + String(int(game.mx)) + "," + String(int(game.my)) + ")";
            if (game.hascontrol && game.deathseq == -1 && game.lifeseq <= 5)
            {
                state.alive = true;
            }
        }
    }

    if (!state.alive) {
        return;
    }

    state.activeEnemies.clear();

    for (entclass &entity : obj.entities) {
        if (!entity.active || entity.invis || entity.type != 23) {
            continue;
        }

        Direction direction;

        if (entity.behave == 0) {
            direction = DirectionRight;
        } else {
            direction = DirectionLeft;
        }

        state.activeEnemies.push_back({direction, entity.xp, entity.yp});
    }

    state.playerXPosition = player->xp;
    state.playerYPosition = player->yp;
    state.playerXVelocity = player->vx;
    state.playerYVelocity = player->vy;

    //fprintf(stderr, "Player (%d, %d) X-velocity (%f, %f)\n", state.playerXp, state.playerYp, state.playerVx, state.playerVy);

    for (Enemy &enemy : state.activeEnemies) {
        std::string directionDescription;

        if (enemy.direction == DirectionRight) {
            directionDescription = "right";
        } else {
            directionDescription = "left";
        }

        //fprintf(stderr, "- Object (%d, %d) travelling %s\n", enemy.xp, enemy.yp, directionDescription.c_str());

    }

}

bool SWNHook::pressLeft() {
    return lastPressedDirection == PressedDirectionLeft;
}

bool SWNHook::pressRight() {
    return lastPressedDirection == PressedDirectionRight;
}
