class TradingRewards:
    def __init__(self):
        pass

    def reward_1(self, action, twap):
        return -abs(action - twap) / (0.4 * twap)

    def reward_2(self, action, twap, is_action, is_twap):
        if is_action > is_twap and action > twap:
            return 1
        return 0

    def reward_3(self, action, twap, avg_plus_set, avg_minus_set, avg_normal_set):
        avg_is_plus = avg_normal_set- avg_plus_set
        avg_is_minus = avg_minus_set- avg_normal_set

        if avg_is_plus > avg_is_minus + abs(avg_is_minus) or avg_is_plus > avg_is_minus + 1:
            i = 1
        elif avg_is_plus < avg_is_minus - abs(avg_is_minus) or avg_is_plus < avg_is_minus - 1:
            i = -1
        elif avg_is_plus > avg_is_minus + 0.1 * abs(avg_is_minus) or avg_is_plus > avg_is_minus + 0.1:
            i = 0.5
        elif avg_is_plus < avg_is_minus - 0.1 * abs(avg_is_minus) or avg_is_plus < avg_is_minus - 0.1:
            i = -0.5
        else:
            i = 0

        return i * max(0, (action - twap) / (0.2 * twap))

    def reward_4(self, action, twap, is_func):
        if is_func(action) > 0 and is_func(action + 0.1 * twap) <= 0:
            return 1 + max(0, (action - twap) / (0.2 * twap))
        return 0

    def reward_5(self, action, twap, is_func):
        if is_func(action) == 0 and action >= 0.8 * twap and is_func(action + 0.1 * twap) < 0:
            return 0.5 + 0.5 * max(0, (action - 0.8 * twap) / (0.2 * twap))
        return 0

    def reward_6(self, action, twap, is_t, is_t_minus_1, is_1):
        if (is_t > is_t_minus_1 + abs(is_t_minus_1) or is_t > is_t_minus_1 + 1 or
                is_t > is_1 + abs(is_1) or is_t > is_1 + 1 or
                is_t < is_t_minus_1 - abs(is_t_minus_1) or is_t < is_t_minus_1 - 1 or
                is_t < is_1 - abs(is_1) or is_t < is_1 - 1):
            i = 1
        elif (is_t > is_t_minus_1 + 0.1 * abs(is_t_minus_1) or is_t > is_t_minus_1 + 0.1 or
              is_t > is_1 + 0.1 * abs(is_1) or is_t > is_1 + 0.1 or
              is_t < is_t_minus_1 - 0.1 * abs(is_t_minus_1) or is_t < is_t_minus_1 - 0.1 or
              is_t < is_1 - 0.1 * abs(is_1) or is_t < is_1 - 0.1):
            i = 0.5
        else:
            i = 0

        if action > twap:
            return i * (1 + (action - twap) / (0.2 * twap))
        else:
            return i * (1 - (action - twap) / (0.2 * twap))

    def reward_7(self, action, twap):
        return -40 * abs(action - twap) / twap

    def calculate_reward(self, action, twap, is_action, is_twap, avg_plus_set, avg_minus_set, avg_normal_set, is_func, is_t, is_t_minus_1, is_1,
                         is_final_step):
        if is_final_step:
            return self.reward_7(action, twap)

        rewards = [
            self.reward_1(action, twap),
            self.reward_2(action, twap, is_action, is_twap),
            self.reward_3(action, twap, avg_plus_set, avg_minus_set, avg_normal_set),
            self.reward_4(action, twap, is_func),
            self.reward_5(action, twap, is_func),
            self.reward_6(action, twap, is_t, is_t_minus_1, is_1)
        ]
        # ic(self.reward_1(action, twap))
        # ic(self.reward_2(action, twap, is_action, is_twap))
        # ic(self.reward_3(action, twap, avg_plus_set, avg_minus_set, avg_normal_set))
        # ic(self.reward_4(action, twap, is_func))


        return sum(rewards)


