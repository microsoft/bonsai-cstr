%% Run the Chemical Process Optimization sample without Bonsai
clear; close all; clc;

%% Initialize Workspace 

% Initialize model params (reused for bonsai training)
init_vars

open_system('CSTR_PI')

% Set Refrence Signal
Cref_signal = 2;

% Percentage of noise to include
noise = 5;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% SCENARIO 1: Using Constant Gains (No Lookup)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% PI Controller

Kp_vec = ones(1, length(Cr_vec)) * -2.00046148741648;
Ki_vec = ones(1, length(Cr_vec)) * -7.98512854300473;

% Lead Controller
Kt_vec = ones(1, length(Cr_vec)) * 3.60620000481947;
a_vec = ones(1, length(Cr_vec)) * 0.384207621232031;
b_vec = ones(1, length(Cr_vec)) * 0.0628087670628903;

sim('CSTR_PI')
% Calculate metrics
metric_rms_C_bench = sqrt(mean((simout(:, 1) - simout(:, 2)).^2));
disp(['Constant Gains: Target Concentration followed with RMS of: ', num2str(metric_rms_C_bench)])

metric_rms_T_bench = sqrt(mean((simout(:, 3) - simout(:, 4)).^2));
disp(['Constant Gains: Target Reactor Temperature followed with RMS of: ', num2str(metric_rms_T_bench)])

plot_results(tout, simout)

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% SCENARIO 2: Using Gain Scheduled PI (Benchmark)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% To prevent thermal runaway while ramping down the residual concentration,
% use feedback control to adjust the coolant temperature |Tc| based on
% measurements of the residual concentration |Cr| and reactor temperature |Tr|.
% For this application, we use a cascade control architecture where
% the inner loop regulates the reactor temperature and the outer loop tracks
% the concentration setpoint. Both feedback loops are digital with a 
% sampling period of 0.5 minutes.


sim('CSTR_PI')

simout_PI = simout;
tout_PI = tout;

% Calculate metrics
metric_rms_C_bench = sqrt(mean((simout_PI(:, 1) - simout_PI(:, 2)).^2));
disp(['Benchmark: Target Concentration followed with RMS of: ', num2str(metric_rms_C_bench)])

metric_rms_T_bench = sqrt(mean((simout_PI(:, 3) - simout_PI(:, 4)).^2));
disp(['Benchmark: Target Reactor Temperature followed with RMS of: ', num2str(metric_rms_T_bench)])

plot_results(tout_PI, simout_PI)

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% SCENARIO 3: Benchmark (with 5% noise)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

noise_magnitude = noise/100;
% Auxiliary params
conc_noise = abs(CrEQ(1)-CrEQ(5))*noise_magnitude;
temp_noise = abs(TrEQ(1)-TrEQ(5))*noise_magnitude;

sim('CSTR_PI')

simout_PI_noise = simout;
tout_PI_noise = tout;

% Calculate metrics
metric_rms_C_bench_5 = sqrt(mean((simout_PI_noise(:, 1) - simout_PI_noise(:, 2)).^2));
disp(['Stretch Benchmark (5% noise): Target Concentration followed with RMS of: ', num2str(metric_rms_C_bench_5)])

metric_rms_T_bench_5 = sqrt(mean((simout_PI_noise(:, 3) - simout_PI_noise(:, 4)).^2));
disp(['Stretch Benchmark (5% noise): Target Reactor Temperature followed with RMS of: ', num2str(metric_rms_T_bench_5)])

plot_results(tout_PI_noise, simout_PI_noise)

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Initialize Default Variables to avoid issues with Bonsai training
% i.e. signal builder
% no noise, etc
init_vars

function [] = plot_results(tout, simout)
    figure
    subplot(311)
    plot(tout, simout(:, 1))
    hold on
    plot(tout, simout(:, 2))
    hold off
    legend('Ref', 'Actual')
    grid, title('Residual concentration'), ylabel('Cr')

    subplot(312)
    plot(tout, simout(:, 3))
    hold on
    plot(tout, simout(:, 4))
    hold off
    legend('Ref', 'Actual')
    grid, title('Reactor temperature'), ylabel('Tr')

    subplot(313)
    plot(tout, simout(:, 5))
    hold on
    plot(tout, simout(:, 6))
    plot(tout, simout(:,7))
    hold off
    legend('dTc', 'dTc rate limited','Tc')
    grid, title('Coolant temperature'), ylabel('Kelvin')
end
