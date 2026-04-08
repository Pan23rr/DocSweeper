# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""FastAPI application for the Doc Sweeper Environment."""

from openenv.core.env_server import create_app

from models import DocAction, DocObservation
from .cust_env_environment import DocSweeperEnvironment

# Create the FastAPI app
# Pass the class (factory) instead of an instance for WebSocket session support
app = create_app(DocSweeperEnvironment, DocAction, DocObservation, env_name="doc_sweeper")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)