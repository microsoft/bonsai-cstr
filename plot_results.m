function [] = plot_results(tout, simout, scenario)
    figure
    sgtitle(scenario)
    subplot(311)
    plot(tout, simout(:, 1))
    hold on
    plot(tout, simout(:, 2))
    hold off
    legend('Ref', 'Actual')
    grid, title('Residual concentration'), ylabel('Cr (kmol/m^3)')

    subplot(312)
    plot(tout, simout(:, 3))
    hold on
    plot(tout, simout(:, 4))
    hold off
    legend('Ref', 'Actual')
    grid, title('Reactor temperature'), ylabel('Tr (K)')

    subplot(313)
    plot(tout, simout(:, 6))
    grid, title('Change to Coolant Temp'), ylabel('Temp (K)')
end
