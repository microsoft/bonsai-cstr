% Copyright (c) Microsoft Corporation.
% Licensed under the MIT License.

function config = bonsaiConfig

    config = BonsaiConfiguration();

    try
        % bonsai workspace ID, see https://preview.bons.ai/accounts/settings
        % SIM_WORKSPACE = 00000000-0000-0000-0000-000000000000
        config.workspace = env("SIM_WORKSPACE");
   
        % access key, generated from https://preview.bons.ai/accounts/settings
        config.accessKey = env("SIM_ACCESS_KEY");

        % Local endpoint for exported brain prediction API
        % BRAINURL = http://localhost:5000/v1/prediction
        config.exportedBrainUrl = env('BRAINURL');
    catch ME
        disp("Missing environment varibles. Copy template.env file to .env and add there.");
        disp("See the following link for details:");
        disp("https://docs.microsoft.com/en-us/bonsai/guides/run-a-local-sim?tabs=bash%2Ctest-with-ui&pivots=sim-lang-simulink#step-3-configure-the-bonsai-cli-and-your-environment")
        rethrow(ME)
    end

    % simulator name, for an unmanaged simulator launched from the desktop to show up on the web
    config.name = "Simulink - Chemical Process";

    % set state and action schemas (overrides data from bonsaiBlock)
    config.stateSchema = ["Cr", "Tr", "Cref", "Tref", "Tc"];
    config.actionSchema = ["Tc_adjust"];
    config.configSchema = ["Cref_signal", "noise_percentage"];

    % time (in sconds) the simulator gateway should wait for
    %  your simulator to advance, defaults to 60
    config.timeout = 60;

    % path to csv file where episode data should be logged
    config.outputCSV = "training.csv";

    % time (in seconds) the simulator gateway should wait for
    % %   your simulator to advance, defaults to 60
    config.timeout = 60;

    % display verbose logs
    config.verbose = false;
end
