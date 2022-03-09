function [] = plot_results(tout, simout, scenario)
    figure
    sgtitle(scenario)
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
    %plot(tout, simout(:, 5))
    hold on
    plot(tout, simout(:, 6))
    hold off
    grid, title('Change to Coolant Temp'), ylabel('Kelvin')
end
