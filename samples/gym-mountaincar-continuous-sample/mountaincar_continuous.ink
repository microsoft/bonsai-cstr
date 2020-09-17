# Inkling code for driving a car up a mountain.
# Simulator source code:
# https://github.com/BonsaiAI/bonsai-sdk/blob/master/samples/openai-gym/gym-mountaincar-continuous-sample/mountaincar_continuous_simulator.py

inkling "2.0"

experiment {
    max_step_per_concept: "1000000"
}

type GameState {
    x_position: number,
    x_velocity: number
}

const ThrottleMin = -1.0
const ThrottleMax = 1.0
type Action {
    command: number<ThrottleMin .. ThrottleMax>
}

type MountainCarConfig {
    deque_size: -1
}

simulator MountainCarSimulator(action: Action, config: MountainCarConfig): GameState {
}

graph (input: GameState): Action {
    concept HighScore(input): Action {
        curriculum {
            source MountainCarSimulator
        }
    }
    output HighScore
}
