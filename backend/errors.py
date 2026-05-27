class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("Validation error")
        self.errors = errors
