#pragma once
#ifndef AF_UNIX_H
#define AF_UNIX_H

#ifdef _WIN32
#ifndef AF_UNIX
#define AF_UNIX 1
#endif
#ifndef SOCK_SEQPACKET
#define SOCK_SEQPACKET 5
#endif
struct sockaddr_un {
    unsigned short sun_family;
    char sun_path[108];
};
#endif

#endif
