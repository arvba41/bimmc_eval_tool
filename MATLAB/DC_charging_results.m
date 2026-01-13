%% Plots for DC charging 
%% Number of parallel cells
figure(2)
clf

subplot(231)
plot(NoofCells,[squeeze(NoofParallel_mosfets_mtx(1,:,1)); squeeze(NoofParallel_mosfets_DC_chrg_mtx(1,:,1))],'x-')
grid on
xlabel('N_{s,cells} [-]')
ylabel('N_{p,cells}^{DSHB} [-]')
legend('Charging','Driving')
ax1 = gca;

subplot(232)
plot(NoofCells,[squeeze(NoofParallel_mosfets_mtx(1,:,3)); squeeze(NoofParallel_mosfets_DC_chrg_mtx(1,:,2))],'x-')
grid on
xlabel('N_{s,cells} [-]')
% ylabel('N_{p,cells}^{Driving} [-]')
% legend('DSHB','DSFB')
ax2 = gca;

subplot(233)
plot(NoofCells,[squeeze(NoofParallel_mosfets_mtx(1,:,3)); squeeze(NoofParallel_mosfets_DC_chrg_mtx(1,:,3))],'x-')
grid on
xlabel('N_{s,cells} [-]')
% ylabel('N_{p,cells}^{Driving} [-]')
% legend('DSHB','DSFB')
ax3 = gca;

subplot(234)
plot(NoofCells,[squeeze(NoofParallel_mosfets_mtx(2,:,1)); squeeze(NoofParallel_mosfets_DC_chrg_mtx(2,:,1))],'x-')
grid on
xlabel('N_{s,cells} [-]')
ylabel('N_{p,cells}^{DSFB} [-]')
% legend('DSHB','DSFB')
ax4 = gca;

subplot(235)
plot(NoofCells,[squeeze(NoofParallel_mosfets_mtx(2,:,2)); squeeze(NoofParallel_mosfets_DC_chrg_mtx(2,:,2))],'x-')
grid on
xlabel('N_{s,cells} [-]')
% ylabel('N_{p,cells}^{Charging} [-]')
% legend('DSHB','DSFB')
ax5 = gca;

subplot(236)
plot(NoofCells,[squeeze(NoofParallel_mosfets_mtx(2,:,3)); squeeze(NoofParallel_mosfets_DC_chrg_mtx(2,:,3))],'x-')
grid on
xlabel('N_{s,cells} [-]')
% ylabel('N_{p,cells}^{Charging} [-]')
% legend('DSHB','DSFB')
ax6 = gca;

linkaxes([ax1 ax2 ax3 ax4 ax5 ax6],'xy')

%% Losses plots
figure(3)
clf

subplot(231)
plot(NoofCells,[squeeze(Psc_tot_max_mtx(1,:,1)); squeeze(Psc_tot_max_DC_chrg_mtx(1,:,1))]/1e3,'x-')
grid on
xlabel('N_{s,cells} [-]')
ylabel('P_{sc(tot)}^{DSHB} [kW]')
legend('Driving','Charging')
ax1 = gca;

subplot(232)
plot(NoofCells,[squeeze(Psc_tot_max_mtx(1,:,3)); squeeze(Psc_tot_max_DC_chrg_mtx(1,:,2))]/1e3,'x-')
grid on
xlabel('N_{s,cells} [-]')
% ylabel('N_{p,cells}^{Driving} [-]')
% legend('DSHB','DSFB')
ax2 = gca;

subplot(233)
plot(NoofCells,[squeeze(Psc_tot_max_mtx(1,:,3)); squeeze(Psc_tot_max_DC_chrg_mtx(1,:,3))]/1e3,'x-')
grid on
xlabel('N_{s,cells} [-]')
% ylabel('N_{p,cells}^{Driving} [-]')
% legend('DSHB','DSFB')
ax3 = gca;

subplot(234)
plot(NoofCells,[squeeze(Psc_tot_max_mtx(2,:,1)); squeeze(Psc_tot_max_DC_chrg_mtx(2,:,1))]/1e3,'x-')
grid on
xlabel('N_{s,cells} [-]')
ylabel('P_{sc(tot)}^{DSFB} [kW]')
% legend('DSHB','DSFB')
ax4 = gca;

subplot(235)
plot(NoofCells,[squeeze(Psc_tot_max_mtx(2,:,2)); squeeze(Psc_tot_max_DC_chrg_mtx(2,:,2))]/1e3,'x-')
grid on
xlabel('N_{s,cells} [-]')
% ylabel('N_{p,cells}^{Charging} [-]')
% legend('DSHB','DSFB')
ax5 = gca;

subplot(236)
plot(NoofCells,[squeeze(Psc_tot_max_mtx(2,:,3)); squeeze(Psc_tot_max_DC_chrg_mtx(2,:,3))]/1e3,'x-')
grid on
xlabel('N_{s,cells} [-]')
% ylabel('N_{p,cells}^{Charging} [-]')
% legend('DSHB','DSFB')
ax6 = gca;

linkaxes([ax1 ax2 ax3 ax4 ax5 ax6],'xy')