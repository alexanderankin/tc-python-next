def get_down_command(options: set[str]) -> str:
    pass


def get_up_command(options: set[str]) -> str:
    pass


def _get_options_as_string(options: set[str]) -> str:
    options_string = " ".join(options)
    if len(options_string) != 0:
        # ensures that there is a space between the options and 'up' if options are passed.
        return options_string
    else:
        # otherwise two spaces would appear between 'docker-compose' and 'up'
        return ""
