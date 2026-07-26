#ifndef MINGW_THREAD_COMPAT_H
#define MINGW_THREAD_COMPAT_H

#if defined(_WIN32) && !defined(_GLIBCXX_HAS_GTHREADS)
#include <windows.h>
#include <process.h>
#include <algorithm>
#include <functional>
#include <type_traits>

namespace std {
    class mutex {
    public:
        mutex() { InitializeCriticalSection(&cs_); }
        ~mutex() { DeleteCriticalSection(&cs_); }
        void lock() { EnterCriticalSection(&cs_); }
        void unlock() { LeaveCriticalSection(&cs_); }
    private:
        CRITICAL_SECTION cs_;
    };

    struct thread_base {
        virtual ~thread_base() {}
        virtual void run() = 0;
    };

    template <typename F>
    struct thread_derived : public thread_base {
        F f_;
        thread_derived(F&& f) : f_(std::forward<F>(f)) {}
        void run() override { f_(); }
    };

    class thread {
    private:
        static unsigned __stdcall run_helper(void* arg) {
            auto base = static_cast<thread_base*>(arg);
            base->run();
            delete base;
            return 0;
        }
    public:
        thread() : handle_(NULL) {}
        template <typename F>
        explicit thread(F&& f) {
            auto base = new thread_derived<typename std::decay<F>::type>(std::forward<F>(f));
            handle_ = (HANDLE)_beginthreadex(NULL, 0, run_helper, base, 0, NULL);
        }
        ~thread() {
            if (handle_) CloseHandle(handle_);
        }
        bool joinable() const { return handle_ != NULL; }
        void detach() {
            if (handle_) {
                CloseHandle(handle_);
                handle_ = NULL;
            }
        }
    private:
        HANDLE handle_;
    };
}
#endif

#endif // MINGW_THREAD_COMPAT_H
