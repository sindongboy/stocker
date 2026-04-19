class StockerError(Exception):
    pass

class BrokerError(StockerError):
    pass

class PermissionDenied(StockerError):
    pass

class StrategyError(StockerError):
    pass

class RiskLimitBreached(StockerError):
    pass
