%% FFT of a signal
function [X_cpx,f] = FFT_function_3d(x,t)
% x, input data
% t, Time vector 

L = length(t); % Sample length
dt = mean(diff(t)); % sampling period
fs= 1/dt; % sampling frequency

% figure(1)
% subplot(311)
% plot(t*1000,data)
% title('Data')
% xlabel('time [ms]')
% ylabel('X(t)')

Y = fft(x,[],3); % Computing FFT
P2 = Y/L; % Dual side-band spectrum

X = P2(:,:,1:L/2+1); % single sided spectrum based on even value of L
X(:,:,2:end-1) = 2*X(:,:,2:end-1);

f = fs*(0:(L/2))/L; % frequency 

% mf = 

% f_idx = find(f < f_fun + mean(diff(f))/2 & f > f_fun - mean(diff(f))/2 );% Index corresponding to fundamental

X_cpx = X/sqrt(2);% RMS Spectra 
X_cpx(:,:,1) = X(:,:,1);

% subplot(3,1,2:3)
% bar(f,P1/P1(f_idx)) 
% grid on
% title('Single-Sided Amplitude Spectrum of Data)')
% xlabel('Harmonic order')
% ylabel('|X(f)|')
% xlim([0 50])