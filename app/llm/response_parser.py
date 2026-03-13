def parse_api_response(api_response):

    """
    Converts HRMS API JSON into a clean structured text
    before sending it to the LLM.
    """

    if not api_response:
        return "No data found."

    # If response is a list
    if isinstance(api_response, list):

        results = []

        for item in api_response:

            if isinstance(item, dict):
                values = [str(v) for v in item.values()]
                results.append(" - ".join(values))

            else:
                results.append(str(item))

        return "\n".join(results)

    # If response is a dictionary
    if isinstance(api_response, dict):

        results = []

        for key, value in api_response.items():
            results.append(f"{key}: {value}")

        return "\n".join(results)

    return str(api_response)


def clean_response(response: str) -> str:
    """
    Cleans LLM output
    """

    return response.strip()