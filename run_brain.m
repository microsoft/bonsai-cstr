%% Run the sample with benchmark and brain and plot results
% This script can be run once you have trained, exported, and are locally
% running a brain.
% This script will run 4 simulation scenarios:
% 1st: Gain scheduled PI without noise
% 2nd: Gain scheduled PI with noise (as configured below)
% 3rd: Brain with no noise
% 4th: Brain with noise (as configured below)

clear; close all; clc;

%% Set simulation configuration

% Set Cref_signal
signal = 2;

% Set noise
% configure noise 1:
noise = 5; % in percentage
 
%% Initialize Workspace for Benchmark

% Initialize model params (reused for bonsai training)
init_vars

open_system('CSTR_PI')

Cref_signal = signal;


%% Run Benchmark without noise

% PI Controller
Kp_vec = [-2.00046148741648;-2.3184560846763;-2.65393524901532;-3.00689898043353;-3.37734727893094;-3.76528014450754;-4.17069757716334;-4.59359957689834;-5.03398614371254;-5.49185727760593;-5.96721297857851;-6.4600532466303;-6.97037808176128;-7.49818748397146;-8.04348145326083];
Ki_vec = [-7.98512854300473;-6.23612330817463;-4.75246287755465;-3.53414725114479;-2.58117642894504;-1.8935504109554;-1.47126919717588;-1.31433278760647;-1.42274118224718;-1.796494381098;-2.43559238415893;-3.34003519142998;-4.50982280291114;-5.94495521860242;-7.64543243850381];

% Lead Controller
Kt_vec = [3.60620000481947;3.57285570622906;3.55992955218359;3.56742154268306;3.59533167772747;3.64365995731683;3.71240638145112;3.80157095013036;3.91115366335453;4.04115452112365;4.19157352343771;4.36241067029671;4.55366596170065;4.76533939764953;4.99743097814336];
a_vec = [0.384207621232031;0.492686723524811;0.580956543031792;0.649017079752974;0.696868333688357;0.72451030483794;0.731942993201725;0.71916639877971;0.686180521571896;0.632985361578283;0.55958091879887;0.465967193233659;0.352144184882648;0.218111893745838;0.0638703198232284];
b_vec = [0.0628087670628903;0.0875474545057933;0.110088960048547;0.130433283691153;0.148580425433609;0.164530385275917;0.178283163218075;0.189838759260085;0.199197173401946;0.206358405643658;0.211322455985221;0.214089324426636;0.214659010967901;0.213031515609018;0.209206838349985];

sim('CSTR_PI')

simout_PI = simout;
tout_PI = tout;

%% Run Benchmark with noise

% Percentage of noise to include
noise_magnitude = noise/100;

% Auxiliary params
conc_noise = abs(CrEQ(1)-CrEQ(5))*noise_magnitude;
temp_noise = abs(TrEQ(1)-TrEQ(5))*noise_magnitude;

sim('CSTR_PI')

simout_PI_noise = simout;
tout_PI_noise = tout;

%% Initialize Workspace for Brain

% Initial data required for compilation should be initialized
init_vars

% load model and disable fast restart
mdl = 'CSTR_Bonsai';
load_system(mdl);
set_param(mdl, 'FastRestart', 'off');

init_vars

open_system('CSTR_Bonsai')

Cref_signal=signal;

%% Run Brain without noise

sim('CSTR_Bonsai');

tout_b = tout;
simout_b = simout;

%% Run Brain with noise

% Percentage of noise to include
noise_magnitude = noise/100;

% Auxiliary params
conc_noise = abs(CrEQ(1)-CrEQ(5))*noise_magnitude;
temp_noise = abs(TrEQ(1)-TrEQ(5))*noise_magnitude;

sim('CSTR_Bonsai');

tout_b_noise = tout;
simout_b_noise = simout;

%% Plot

plot_comparison(tout_b, simout_b,tout_b_noise, simout_b_noise,...
    tout_PI, simout_PI,tout_PI_noise, simout_PI_noise,noise)


%%
function []=plot_comparison(tout_b, simout_b,tout_b_noise, simout_b_noise,...
    tout_PI, simout_PI,tout_PI_noise, simout_PI_noise, noise)

    % Calculate Error RMS of concentration
    metric_rms_C_bench = sqrt(mean((simout_PI(:, 1) - simout_PI(:, 2)).^2));
    metric_rms_C_bench_noise = sqrt(mean((simout_PI_noise(:, 1) - simout_PI_noise(:, 2)).^2));
    metric_rms_C_brain = sqrt(mean((simout_b(:, 1) - simout_b(:, 2)).^2));
    metric_rms_C_brain_noise = sqrt(mean((simout_b_noise(:, 1) - simout_b_noise(:, 2)).^2));
    
    % Calculate percentage improvement of Brain over Benchmark
    improvement = (metric_rms_C_bench - metric_rms_C_brain)/metric_rms_C_bench * 100;
    improvement_noise = (metric_rms_C_bench_noise - metric_rms_C_brain_noise)/metric_rms_C_bench_noise * 100;
    
    % Display % Improvement 
    txt = ['Brain shows' num2str(improvement) '% Improvement over benchmark with no noise']
    txt = ['Brain shows' num2str(improvement_noise) '% Improvement over benchmark with' num2str(noise) 'noise']

    
    % Generate bar graph variables
    x = categorical({'Benchmark', 'Brain'});
    x = reordercats(x, {'Benchmark', 'Brain'});
    y = [metric_rms_C_bench metric_rms_C_brain]; 

    x5 = categorical({'Benchmark', 'Brain'});
    x5 = reordercats(x5, {'Benchmark', 'Brain'});
    y5 = [metric_rms_C_bench_noise metric_rms_C_brain_noise];
    
    % Find max temp reached
    Tmax_bench = max(simout_PI(:,4));
    Tmax_bench_5 = max(simout_PI_noise(:,4));
    Tmax_brain = max(simout_b(:,4));
    Tmax_brain_5 = max(simout_b_noise(:,4));

    % Generate bar graph variables
    xT = categorical({'Benchmark', 'Brain'});
    xT = reordercats(xT, {'Benchmark', 'Brain'});
    yT = [Tmax_bench; Tmax_brain];

    xT5 = categorical({'Benchmark', 'Brain'});
    xT5 = reordercats(xT5, {'Benchmark', 'Brain'});
    yT5 = [Tmax_bench_5; Tmax_brain_5];
    
    figure
    sgtitle('Bonsai Brain vs. Benchmark (Gain Scheduled PI Control)')
    
    % plot results with 0% noise
    subplot(421) 
        plot(tout_b, simout_b(:, 1),'LineStyle','--')
        hold on
        plot(tout_b, simout_b(:, 2),'color','blue')
        plot(tout_PI, simout_PI(:, 2),'color','red')
        hold off
        ylim([0 11])
        legend('Ref', 'Brain','Benchmark','Location','southwest')
        grid, title('0% noise simulated'), ylabel('Residual Concentration (Cr)')

    subplot(423)
        plot(tout_b, simout_b(:, 3),'LineStyle','--')
        hold on
        plot(tout_b, simout_b(:, 4),'color','blue')
        plot(tout_PI, simout_PI(:, 4),'color','red')
        hold off
        ylim([250 450])
        legend('Ref', 'Brain','Benchmark','Location','northwest')
        grid, ylabel('Reactor Temperature (Tr)'), xlabel ('time (s)')
    
    % plot results 5% noise
    subplot(422)
        plot(tout_b_noise, simout_b_noise(:, 1),'LineStyle','--')
        hold on
        plot(tout_b_noise, simout_b_noise(:, 2),'color','blue')
        plot(tout_PI_noise, simout_PI_noise(:, 2),'color','red')
        hold off
        ylim([0 11])
        legend('Ref', 'Brain','Benchmark','Location','southwest')
        grid, title([num2str(noise),'% noise simulated']), ylabel('Residual Concentration (Cr)')

    subplot(424)
        plot(tout_b_noise, simout_b_noise(:, 3),'LineStyle','--')
        hold on
        plot(tout_b_noise, simout_b_noise(:, 4),'color','blue')
        plot(tout_PI_noise, simout_PI_noise(:, 4),'color','red')
        hold off
        ylim([250 450])
        legend('Ref', 'Brain','Benchmark','Location','northwest')
        grid, ylabel('Reactor Temperature (Tr)'), xlabel ('time (s)')
    
    % Plot Error RMS of Cencentration
    subplot(425)
        bar(x,y);
        ylabel('RMS of error'),
        ylim([0 5])

     subplot(426)
         bar(x5,y5)
         ylabel('RMS of error'),
         ylim([0 5])

     % Plot max temp
     subplot(427)
         bar(xT,yT)
         hold on
         yline(400,'LineStyle','--','LineWidth',2)
         title('Max Temperature - 0% noise simulated'),
         ylabel('Reactor Temperature'),
         ylim([0 500])

     subplot(428)
         bar(xT5,yT5)
         hold on
         yline(400,'LineStyle','--','LineWidth',2)
         title(['Max Temperature - ',num2str(noise),'% noise simulated'])
         ylabel('Reactor Temperature'),
         ylim([0 500])

end

