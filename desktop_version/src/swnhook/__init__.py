venv = "../../python3.8-venv/bin/activate_this.py"
exec(open(venv).read(), {'__file__': venv})

import os
from pprint import pprint
import random
import threading
import queue
import collections
import math

import neat

QueueMessage = collections.namedtuple('QueueMessage', ('state', 'result_queue'))
GenerationStatus = collections.namedtuple('GenerationStatus', ('current', 'previous', 'previous_best_fitness'))
RunResult = collections.namedtuple('RunResult', ('pressed_direction', 'generation_status', 'genome_number', 'current_generation_best_fitness'))

PRESSED_DIRECTION_NONE = 0
PRESSED_DIRECTION_LEFT = -1
PRESSED_DIRECTION_RIGHT = 1

class SWNHookReporter(neat.reporting.BaseReporter):
    def __init__(self):
        self.generation_status_lock = threading.Lock()
        self.generation_status = GenerationStatus(None, None, None)

    def start_generation(self, generation):
        with self.generation_status_lock:
            self.generation_status = self.generation_status._replace(current=generation)

    def end_generation(self, config, population, species_set):
        with self.generation_status_lock:
            self.generation_status = self.generation_status._replace(current=None,
                                                                     previous=self.generation_status.current,
                                                                     previous_best_fitness=self._get_best_fitness(species_set))

    def _get_best_fitness(self, species_set):
        species = list(species_set.species.values())
        fitnesses = [[fitness for fitness in s.get_fitnesses() if fitness is not None] for s in species]
        best_fitnesses = [max(species_fitnesses or (0,)) for species_fitnesses in fitnesses]
        best_fitness = max(best_fitnesses or (0,))

        return best_fitness


    def get_current_status(self):
        with self.generation_status_lock:
            return self.generation_status

def clamp(value, min_, max_):
    return max(min_, min(max_, value))

class Main:

    def _eval_genomes(self, genomes, config):
        # print("_eval_genomes: Starting")

        # Idea: inputs is a grid of the board?
        # Fitness function considers if AI changes input to avoid (or cause) an imminent collision (in the next n seconds?)

        for (genome_number, (genome_id, genome)) in enumerate(genomes):
            net = neat.ctrnn.CTRNN.create(genome, config, 1)
            net.reset()

            # net = neat.nn.FeedForwardNetwork.create(genome, config)

            with self.current_genome_lock:
                self.current_genome = genome_number

            # print("_eval_genomes: Genome #{} awaiting next life".format(genome_number))

            while True:
                message = self.queue.get()
                # wait for player to gain control
                if message.state['inGame'] and message.state['alive']:
                    break
                message.result_queue.put(PRESSED_DIRECTION_NONE)

            # player now has control

            genome.fitness = 0

            # print("_eval_genomes: Starting new life")

            while True:
                if not message.state['inGame'] or not message.state['alive']:
                    # died, break and return
                    break

                genome.fitness += 1 # survived a frame

                with self.current_genome_lock:
                    self.current_best_fitness = max(self.current_best_fitness or 0, genome.fitness or 0)

                inputs = []

                playerXp = message.state['playerXp']
                playerYp = message.state['playerYp']
                playerVx = message.state['playerVx']
                playerVy = message.state['playerVy']

                min_player_y = 46
                max_player_y = 161
                min_player_x = -9
                max_player_x = 310
                min_player_vx = -6.0
                max_player_vx = 6.0
                min_player_vy = -10.0
                max_player_vy = 10.0
                player_x_size = max_player_x - min_player_x + 1

                inputs.append(clamp((playerXp - min_player_x) / (max_player_x - min_player_x), 0, 1))
                inputs.append(clamp((playerYp - min_player_y) / (max_player_y - min_player_y), 0, 1))
                inputs.append(clamp((playerVx - min_player_vx) / (max_player_vx - min_player_vx), 0, -1))
                inputs.append(clamp((playerVy - min_player_vy) / (max_player_vy - min_player_vy), 0, -1))

                enemies = list(message.state['activeEnemies'])

                enemies_offs = len(inputs)

                # first half inputs are for enemies moving left,
                # next half for enemies moving right,
                # the position matches the rough y position of the enemy, and the value is the distance from the player.
                # 
                # eg. enemies[0] = 16

                enemy_inputs = [None] * 60

                enemies.sort(key=lambda enemy: (
                    enemy['direction'],
                    enemy['xp'] - playerXp
                    ))

                num_slots_per_direction = len(enemy_inputs) // 2
                num_segments_per_direction = 6
                num_slots_per_segment = num_slots_per_direction // num_segments_per_direction

                printed_warning = False

                for enemy in enemies:
                    segment = (enemy['yp'] - 58) // 20

                    direction_offset = num_slots_per_direction if enemy['direction'] > 0 else 0

                    for slot in range(num_slots_per_segment):
                        offset = segment * num_slots_per_segment + slot + direction_offset
                        if enemy_inputs[offset] is None:
                            enemy_inputs[offset] = enemy['xp'] - playerXp
                            break
                    else:
                        print("warning: projectile at y={}, dir={}, distance={} couldn't fit in segment {}".format(enemy['yp'], enemy['direction'], enemy['xp'] - playerXp, segment))
                        printed_warning = True

                if printed_warning:
                    print()

                # change Nones to distant values
                enemy_inputs = ([d if d is not None else 10000 for d in enemy_inputs[:len(enemy_inputs)//2]] +
                                [d if d is not None else -10000 for d in enemy_inputs[len(enemy_inputs)//2:]])

                max_distance = 600

                # try normalizing values between 0 and 1
                enemy_inputs = [clamp(((d / max_distance) + 1) / 2, 0, 1) for d in enemy_inputs]

                inputs.extend(enemy_inputs)

                #pprint(inputs)
                player_xp_norm = inputs[0]
                player_yp_norm = inputs[1]

                draw_width = 80
                draw_xborder = 1

                # --- game board visualization

                # print('---')

                # for segment in range(num_segments_per_direction):
                #     segment_min_y_norm = segment / num_segments_per_direction
                #     segment_max_y_norm = (segment + 1) / num_segments_per_direction
                #     show_player = (segment_min_y_norm <= player_yp_norm < segment_max_y_norm)

                #     segment_draw = [' '] * (draw_width + (draw_xborder * 2))

                #     for direction_offset in (0, num_slots_per_direction):
                #         for slot in range(num_slots_per_segment):
                #             offset = segment * num_slots_per_segment + slot + direction_offset
                #             distance_from_player = enemy_inputs[offset]
                #             if distance_from_player > 0.01 and distance_from_player < 0.99:
                #                 # TODO: this calculation is wrong, and entities appear onscreen even when they aren't - but only if they're far from the player
                #                 entity_xp = ((player_xp_norm * player_x_size) + ((distance_from_player - 0.5) * max_distance)) / player_x_size

                #                 draw_xp = math.floor(entity_xp * draw_width)
                #                 if draw_xp < 0 or draw_xp >= draw_width:
                #                     draw_xp = clamp(draw_xp, -1, draw_width)
                #                     segment_draw[draw_xp] = '|'
                #                 else:
                #                     segment_draw[draw_xp + draw_xborder] = '>' if direction_offset == num_slots_per_direction else '<'

                #     if show_player:
                #         draw_player_xp = clamp(math.floor(player_xp_norm * draw_width), 0, draw_width - 1)
                #         segment_draw[draw_player_xp + draw_xborder] = 'X'

                #     print(''.join(segment_draw))



                # -- enemy positions with direction

                # enemies.sort(key=lambda enemy: abs(message.state['playerXp'] - enemy['xp'])) # nearest enemies first

                # for enemy in enemies[:20]: # support up to 20 enemies
                #     inputs.append(1) # 1 = active enemy slot
                #     inputs.append(enemy['xp'])
                #     inputs.append(enemy['yp'])
                #     inputs.append(enemy['direction'])

                # empty_slots = max(20 - len(enemies), 0)
                # for i in range(empty_slots):
                #     inputs.append(0) # inactive enemy slot
                #     inputs.append(0) # unused
                #     inputs.append(0) # unused
                #     inputs.append(0) # unused

                # action = net.activate(inputs)[0]
                action = net.advance(inputs, 1, 1)[0]

                if action < -0.5:
                    pressed_direction = -1
                    pressed_direction_description = 'left'
                elif action > 0.5:
                    pressed_direction = 1
                    pressed_direction_description = 'right'
                else:
                    pressed_direction = 0
                    pressed_direction_description = 'nothing'

                #print("AI pressed {}".format(pressed_direction_description))

                message.result_queue.put(pressed_direction)

                # pull next message
                message = self.queue.get()

            # print("_eval_genomes: Died or quit with fitness={}".format(genome.fitness))
            message.result_queue.put(PRESSED_DIRECTION_NONE)
    
        with self.current_genome_lock:
            self.current_genome = None
            self.current_best_fitness = 0

        # print("_eval_genomes: Exiting")


    def _start_neat(self):
        self.thread = threading.Thread(target=self._neat_thread)
        self.thread.start()
    
    def _neat_thread(self):

        local_dir = os.path.dirname(__file__)
        config_path = os.path.join(local_dir, 'config-ctrnn') #'config-feedforward.txt')
        config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                             neat.DefaultSpeciesSet, neat.DefaultStagnation,
                             config_path)

        pop = neat.Population(config)
        stats = neat.StatisticsReporter()
        pop.add_reporter(stats)
        pop.add_reporter(self.swnhook_reporter)
        pop.add_reporter(neat.StdOutReporter(True))

        winner = pop.run(self._eval_genomes, math.floor(60 * 24 / 0.5)) # 60 minutes * 24 hours / 0.5 minutes per generation

        print("Winner is {}".format(winner))
        print("Pretty printed:")
        pprint(winner)

        # pe = neat.ParallelEvaluator(multiprocessing.cpu_count(), eval_genome)
        # winner = pop.run(pe.evaluate)

        # Save the winner.
        # with open('winner-ctrnn', 'wb') as f:
        #     pickle.dump(winner, f)

        # print(winner)

        # visualize.plot_stats(stats, ylog=True, view=True, filename="ctrnn-fitness.svg")
        # visualize.plot_species(stats, view=True, filename="ctrnn-speciation.svg")

        # node_names = {-1: 'x', -2: 'dx', -3: 'theta', -4: 'dtheta', 0: 'control'}
        # visualize.draw_net(config, winner, True, node_names=node_names)

        # visualize.draw_net(config, winner, view=True, node_names=node_names,
        #                    filename="winner-ctrnn.gv")
        # visualize.draw_net(config, winner, view=True, node_names=node_names,
        #                    filename="winner-ctrnn-enabled.gv", show_disabled=False)
        # visualize.draw_net(config, winner, view=True, node_names=node_names,
        #                    filename="winner-ctrnn-enabled-pruned.gv", show_disabled=False, prune_unused=True)

    def __init__(self):
        self.max_active_enemies = 0
        self.queue = queue.Queue()
        self.swnhook_reporter = SWNHookReporter()
        self.current_genome_lock = threading.Lock()
        self.current_genome = None
        self.current_best_fitness = 0
        self._start_neat()

    def run(self, state):
        '''
        state is a dict that matches GravitronState from SWNHook.h
        each enemy direction is -1 (left) or 1 (right)

        return RunResult with direction -1 to press left, 1 to press right, 0 to press nothing
        '''

        result_queue = queue.Queue()
        self.queue.put(QueueMessage(state, result_queue))
        direction = result_queue.get()

        generation_status = self.swnhook_reporter.get_current_status()
        with self.current_genome_lock:
            genome_number = self.current_genome
            current_best_fitness = self.current_best_fitness

        return RunResult(direction, generation_status, genome_number, current_best_fitness)

main = Main()

def run(state):
    return main.run(state)

