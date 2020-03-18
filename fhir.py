from apis import Api

def get_bundle(api: Api, endpoint, params=None, count=100) -> Iterable[dict]:
    url = f"{api.base_url}{endpoint}?patient={api.id}&_count={count}"
    while url is not None:
        bundle = api.get(url, params)
        for entry in bundle.get('entry', []):
            resource = entry.get('resource')
            if resource is not None:
                yield resource
        url = None
        for link in bundle.get('link', []):
            if link.get('relation') == 'next':
                url = link.get('url')
                break

def get_lab_results(api: Api) -> Iterable[dict]:
    for resource in get_bundle(api, "Observation"):
        pass