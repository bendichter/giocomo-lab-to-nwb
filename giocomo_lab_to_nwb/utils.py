def check_module(nwbfile, name, description=None):
    """Check if processing module exists. If not, create it. Then return module.
    Parameters
    ----------
    nwbfile: pynwb.NWBFile
    name: str
    description: str | None (optional)
    Returns
    -------
    pynwb.module
    """
    if name in nwbfile.processing:
        return nwbfile.processing[name]
    else:
        if description is None:
            description = name
        return nwbfile.create_processing_module(name, description)
